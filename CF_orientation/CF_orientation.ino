#include <Arduino_LSM9DS1.h> // IMU Sensors
// #include <ArduinoBLE.h>
#include <math.h>

const bool debug_x = false;
const bool debug_y = false;
const bool debug_z = false;
// const bool debug_rssi = true;

// Degrees -> Radians
float deg2rad(float deg) {
  return deg * M_PI / 180.0;
}

// Radians -> Degrees
float rad2deg(float rad) {
  return rad * 180.0 / M_PI;
}

// Map heading to (-M_PI, M_PI]
float map_heading(float heading) {
  while (heading < (-1.0 * M_PI)) {
    heading += (2.0 * M_PI);
  }
  while (heading >= M_PI) {
    heading -= (2.0 * M_PI);
  }
  return heading;
}

// Cross Product of 2 vectors of length 3
void cross_prod(float ax, float ay, float az,
                float bx, float by, float bz,
                float *cx, float *cy, float *cz) {
  *cx = (ay * bz) - (az * by);
  *cy = (az * bx) - (ax * bz); 
  *cz = (ax * by) - (ay * bx);
}

float acc_x, acc_y, acc_z;
float gyro_x, gyro_y, gyro_z;
float mag_x, mag_y, mag_z;

float roll, pitch, heading;

// Variables used to calculate magnetic north
float mag_north_x, mag_north_y, mag_north_z;
float mag_west_x, mag_west_y, mag_west_z;
float X_h, Y_h;

unsigned long delta_t = 0.0;
unsigned long prev_t = millis();
unsigned long mag_delta_t = 0.0;
unsigned long mag_prev_t = millis();
unsigned long rssi_delta_t = 0.0;
unsigned long rssi_prev_t = millis();

bool imu_1st_init = true;
bool mag_1st_init = true;
bool ble_1st_init = true;

// Hard Gyro Offsets: x: 0.02249103942652321, y: -0.48735663082437297, z: 0.7963082437275936
const float gyro_x_offset = .02;
const float gyro_y_offset = -.49;
const float gyro_z_offset = .80;

// Gyro Z Multiplier: z: 1.14
const float gyro_z_multiplier = 1.14;

// Hard Magnetometer Offsets: x: 18.64209607980653, y: 13.395542038195217, Z: 8.798978141729961
const float mag_x_offset = 18.64;
const float mag_y_offset = 13.30;
const float mag_z_offset = 8.80;

// Values to detect motion/rotation
float resultant_acc;
const float acc_threshold = 0.1;
bool in_motion = false;

// Time until sigma_delta_heading is below threshold is porportional to delta_heading_size / (Sampling Rate of Nano 33 BLE: ~20 Hz)
const int motion_history_sum_threshold = 30;
const int in_motion_history_size = 120;
int motion_history_sum;
int in_motion_history[in_motion_history_size] = {0};

float prev_heading;
const float delta_heading_threshold = deg2rad(2.5);
bool is_rotating = false;

// Time until sigma_delta_heading is below threshold is porportional to delta_heading_size / (Sampling Rate of Nano 33 BLE: ~20 Hz)
float sigma_delta_heading;
const int delta_heading_size = 30;
float delta_heading[delta_heading_size] = {1.0};

// Normalize orientation
float initial_roll, initial_pitch, initial_heading;

// Values used in accelometer low pass filter
const float acc_filt_cutoff = 5; // Hz
const float acc_rc = 1 / (2.0 * M_PI * acc_filt_cutoff);
float alpha_alpf;

// Filtered accelometer data
float filt_acc_x;
float filt_acc_y;
float filt_acc_z;

// Previous filtered accelometer data
float prev_filt_acc_x;
float prev_filt_acc_y;
float prev_filt_acc_z;

// Accelometer based roll & pitch
float acc_roll;
float acc_pitch;

// Values used in gyroscope high pass filter
const float gyro_freq_cutoff = .001; // Hz
const float gyro_rc = 1 / (2.0 * M_PI * gyro_freq_cutoff);
float alpha_ghpf;

// Raw integral gyroscope data
float sigma_gyro_x = 0.0;
float sigma_gyro_y = 0.0;
float sigma_gyro_z = 0.0;

// Mapped integral gyroscope Z data 
float mapped_filt_sigma_gyro_z;

// Previous raw integral gyroscope data
float prev_sigma_gyro_x;
float prev_sigma_gyro_y;
float prev_sigma_gyro_z;

// Filtered integral gyroscope data
float filt_sigma_gyro_x;
float filt_sigma_gyro_y;
float filt_sigma_gyro_z;

// Previous filtered integral gyroscope data
float prev_filt_sigma_gyro_x;
float prev_filt_sigma_gyro_y;
float prev_filt_sigma_gyro_z;

// Values used in magnetometer low pass filter
const float mag_freq_cutoff = 5; // Hz
const float mag_rc = 1 / (2.0 * M_PI * mag_freq_cutoff);
float alpha_mlpf;

// Filtered magnetometer data
float filt_mag_x;
float filt_mag_y;
float filt_mag_z;

// Filtered magnetometer data
float prev_filt_mag_x;
float prev_filt_mag_y;
float prev_filt_mag_z;

// Constants for complementary filter
float cf_roll;
const float alpha_roll = .5; // alpha_roll * filt_sigma_gyro_x, (1 - alpha_roll) * filt_roll
float cf_pitch;
const float alpha_pitch = .5; // alpha_pitch * filt_sigma_gyro_y, (1 - alpha_pitch) * filt_pitch
float cf_heading;
const float alpha_heading = .5; // alpha_heading * filt_sigma_gyro_z, (1 - alpha_heading) * heading

// BLE object for advertising connection
/*
BLEDevice central;

float measured_rssi = -49.0;
float rssi;
float dist;

// Values used in RSSI low pass filter
float filt_rssi;
float prev_filt_rssi;
const float rssi_freq_cutoff = 0.25; // Hz
const float rssi_rc = 1 / (2.0 * M_PI * rssi_freq_cutoff);
float alpha_rlpf;
*/

void setup() {
  Serial.begin(9600);
  while(!Serial);

  if(!IMU.begin()) {
    Serial.println("Failed to initialize IMU sensors!");
    while (1);
  }

  /*
  if (!BLE.begin()) {
    Serial.println("Failed to initialize BLE!");
    while (1);
  }
  BLE.setDeviceName("Nano_33_BLE");
  BLE.setLocalName("Nano_33_BLE");
  BLE.advertise();
  Serial.println("Advertising...");
  */
}

void loop() {
  if (IMU.accelerationAvailable() && IMU.gyroscopeAvailable()) {
    IMU.readAcceleration(acc_x, acc_y, acc_z);
    IMU.readGyroscope(gyro_x, gyro_y, gyro_z);

    // IMU time delta
    delta_t = millis() - prev_t;
    prev_t = millis();
    
    // Low pass filter on accelometer data
    alpha_alpf = (delta_t / 1000.0) / (acc_rc + (delta_t / 1000.0));
    filt_acc_x = prev_filt_acc_x + (alpha_alpf * (acc_x - prev_filt_acc_x));
    filt_acc_y = prev_filt_acc_y + (alpha_alpf * (acc_y - prev_filt_acc_y));
    filt_acc_z = prev_filt_acc_z + (alpha_alpf * (acc_z - prev_filt_acc_z)) ;
    prev_filt_acc_x = filt_acc_x;
    prev_filt_acc_y = filt_acc_y;
    prev_filt_acc_z = filt_acc_z;
    
    // Calculate roll and pitch using filtered accelometer data
    acc_pitch = -1.0 * atan2(filt_acc_x, sqrt((filt_acc_y * filt_acc_y) + (filt_acc_z * filt_acc_z)));
    acc_roll = atan2(filt_acc_y, sqrt((filt_acc_x * filt_acc_x) + (filt_acc_z * filt_acc_z)));

    // Account for gyro offsets
    gyro_x -= gyro_x_offset;
    gyro_y -= gyro_y_offset;
    gyro_z -= gyro_z_offset;

    /*
      Conditional high pass filter on integrated gyroscope XY data

      If motion is not detected, overwrite the integrated gryoscope based roll and pitch 
      with those of the accelometer. This helps counter drift on the gryoscope XY axes.
    */
    resultant_acc = sqrt((acc_x * acc_x) + (acc_y * acc_y) + (acc_z * acc_z)) * 100.0;
    motion_history_sum = 0;
    for (int a = in_motion_history_size - 1; a > 0; a--) {
      motion_history_sum += in_motion_history[a];
      in_motion_history[a] = in_motion_history[a - 1];
    }
    in_motion_history[0] = int((abs(100.0 - resultant_acc) / 100.0) > acc_threshold);
    motion_history_sum += in_motion_history[0];
    in_motion = (motion_history_sum > motion_history_sum_threshold);

    is_rotating = (sigma_delta_heading > delta_heading_threshold);
    if (!imu_1st_init && in_motion) {
      sigma_gyro_x += (gyro_x * (delta_t / 1000.0));
      sigma_gyro_y += (gyro_y * (delta_t / 1000.0));
      alpha_ghpf = gyro_rc / (gyro_rc + (delta_t / 1000.0));
      filt_sigma_gyro_x = alpha_ghpf * (prev_filt_sigma_gyro_x + sigma_gyro_x - prev_sigma_gyro_x);
      filt_sigma_gyro_y = alpha_ghpf * (prev_filt_sigma_gyro_y + sigma_gyro_y - prev_sigma_gyro_y);
      prev_sigma_gyro_x = sigma_gyro_x;
      prev_sigma_gyro_y = sigma_gyro_y;
    } else if (!imu_1st_init && !in_motion) {
      filt_sigma_gyro_x = rad2deg(acc_roll);
      filt_sigma_gyro_y = rad2deg(acc_pitch);
    } else if (imu_1st_init) {
      imu_1st_init = false;
      filt_sigma_gyro_x = rad2deg(acc_roll);
      filt_sigma_gyro_y = rad2deg(acc_pitch);
      initial_roll = acc_roll;
      initial_pitch = acc_pitch;
    }
    prev_filt_sigma_gyro_x = filt_sigma_gyro_x;
    prev_filt_sigma_gyro_y = filt_sigma_gyro_y;    

    /*
      High pass filter on integrated gyroscope Z data

      Heading cannot be calculated using an accelometer. It is possible to address drift 
      on the gyroscope Z axis using the magnetometer, which is done further below.
    */
    sigma_gyro_z += (gyro_z * (delta_t / 1000.0) * gyro_z_multiplier);
    alpha_ghpf = gyro_rc / (gyro_rc + (delta_t / 1000.0));
    filt_sigma_gyro_z = alpha_ghpf * (prev_filt_sigma_gyro_z + sigma_gyro_z - prev_sigma_gyro_z);
    prev_sigma_gyro_z = sigma_gyro_z;
    prev_filt_sigma_gyro_z = filt_sigma_gyro_z;
    mapped_filt_sigma_gyro_z = rad2deg(map_heading(deg2rad(filt_sigma_gyro_z)));

    if (IMU.magneticFieldAvailable()) {
      IMU.readMagneticField(mag_x, mag_y, mag_z);

      // Account for magnetometer offset
      mag_x -= mag_x_offset;
      mag_y -= mag_y_offset;
      mag_z -= mag_z_offset;

      // Magnetometer time delta
      mag_delta_t = millis() - mag_prev_t;
      mag_prev_t = millis();

      // Low pass filter on magnetometer data
      alpha_mlpf = (mag_delta_t / 1000.0) / (mag_rc + (mag_delta_t / 1000.0));
      filt_mag_x = prev_filt_mag_x + (alpha_mlpf * (mag_x - prev_filt_mag_x));
      filt_mag_y = prev_filt_mag_y + (alpha_mlpf * (mag_y - prev_filt_mag_y));
      filt_mag_z = prev_filt_mag_z + (alpha_mlpf * (mag_z - prev_filt_mag_z));
      prev_filt_mag_x = filt_mag_x;
      prev_filt_mag_y = filt_mag_y;
      prev_filt_mag_z = filt_mag_z;

      // Complementary filter for roll and pitch using gyroscope and accelometer based roll and pitch
      float cf_roll = (alpha_roll * deg2rad(filt_sigma_gyro_x)) + ((1 - alpha_roll) * acc_roll) - initial_roll;
      float cf_pitch = (alpha_pitch * deg2rad(filt_sigma_gyro_y)) + ((1 - alpha_pitch) * acc_pitch) - initial_pitch;

      // Calculating the heading and adjust as necessary
      cross_prod(filt_acc_x, filt_acc_y, filt_acc_z, -1.0 * filt_mag_x, filt_mag_y, filt_mag_z, &mag_west_x, &mag_west_y, &mag_west_z);
      cross_prod(mag_west_x, mag_west_y, mag_west_z, acc_x, acc_y, acc_z, &mag_north_x, &mag_north_y, &mag_north_z);
      heading = atan2(mag_west_x, mag_north_x);
      if (mag_1st_init) {
        mag_1st_init = false;
        initial_heading = heading;
      }
      heading = map_heading(heading - initial_heading);

      /*
        Determine if the board is rotating. If not in motion or rotating, overwrite the
        integrated gyroscope based heading with that of the magnetometer
      */
      sigma_delta_heading = 0.0;
      for (int a = delta_heading_size - 1; a > 0; a--) {
        sigma_delta_heading += delta_heading[a];
        delta_heading[a] = delta_heading[a-1];
      }
      if (heading - prev_heading > M_PI) {
        delta_heading[0] = heading - prev_heading - (2.0 * M_PI);
      } else if (heading - prev_heading < (-1.0 * M_PI)) {
        delta_heading[0] = heading - prev_heading + (2.0 * M_PI);
      } else {
        delta_heading[0] = heading - prev_heading;
      }
      sigma_delta_heading += delta_heading[0];
      sigma_delta_heading = abs(sigma_delta_heading);
      prev_heading = heading;
      is_rotating = (sigma_delta_heading > delta_heading_threshold);
      if (!in_motion && !is_rotating) {
        sigma_gyro_z = -1.0 * rad2deg(heading);
        filt_sigma_gyro_z = -1.0 * rad2deg(heading);
        prev_filt_sigma_gyro_z = -1.0 * rad2deg(heading);
        mapped_filt_sigma_gyro_z = -1.0 * rad2deg(heading);
      }

      // central = BLE.central();
      // if (central) {
      if (true) {
        // Complementary filter for heading
        if (abs(heading - (-1.0 * deg2rad(mapped_filt_sigma_gyro_z))) > M_PI) {
          if (heading > -1.0 * deg2rad(mapped_filt_sigma_gyro_z)) {
            cf_heading = map_heading((alpha_heading * -1.0 * deg2rad(mapped_filt_sigma_gyro_z) + (2.0 * M_PI)) + ((1 - alpha_heading) * heading));
          } else {
            cf_heading = map_heading((alpha_heading * -1.0 * deg2rad(mapped_filt_sigma_gyro_z)) + ((1 - alpha_heading) * (heading + (2.0 * M_PI))));
          }
        } else {
          cf_heading = map_heading((alpha_heading * -1.0 * deg2rad(mapped_filt_sigma_gyro_z)) + ((1 - alpha_heading) * heading));
        }
        /*
        rssi_delta_t = millis() - rssi_prev_t;
        rssi_prev_t = millis();
        
        // Low pass filter on RSSI data
        rssi = central.rssi();
        if (!ble_1st_init) {
          alpha_rlpf = (rssi_delta_t / 1000.0) / (rssi_rc + (rssi_delta_t / 1000.0));
          filt_rssi = prev_filt_rssi + (alpha_rlpf * (rssi - prev_filt_rssi));
          prev_filt_rssi = filt_rssi;
        } else {
          ble_1st_init = false;
          prev_filt_rssi = rssi;
        }
        dist = pow(10.0, (measured_rssi - rssi) / (10.0 * 2.0));
        */

        // Stream the data
        Serial.print("{");
        if (debug_x) {
          Serial.print("\"initial_roll\": ");
          Serial.print(-1.0 * rad2deg(initial_roll));
          Serial.print(", ");
          Serial.print("\"acc_roll\": ");
          Serial.print(-1.0 * rad2deg(acc_roll));
          Serial.print(", ");
          Serial.print("\"filt_sigma_gyro_x\": ");
          Serial.print(-1.0 * filt_sigma_gyro_x);
          Serial.print(", ");
        }
        Serial.print("\"cf_roll\": ");
        Serial.print(-1.0 * rad2deg(cf_roll));
        Serial.print(", ");
        if (debug_y) {
          Serial.print("\"initial_pitch\": ");
          Serial.print(-1.0 * rad2deg(initial_pitch));
          Serial.print(", ");
          Serial.print("\"acc_pitch\": ");
          Serial.print(-1.0 * rad2deg(acc_pitch));
          Serial.print(", ");
          Serial.print("\"filt_sigma_gyro_y\": ");
          Serial.print(-1.0 * filt_sigma_gyro_y);
          Serial.print(", ");
        }
        Serial.print("\"cf_pitch\": ");
        Serial.print(-1.0 * rad2deg(cf_pitch));
        Serial.print(", ");
        if (debug_z) {
          Serial.print("\"initial_heading\": ");
          Serial.print(rad2deg(initial_heading));
          Serial.print(", ");
          Serial.print("\"heading\": ");
          Serial.print(rad2deg(heading));
          Serial.print(", ");
          Serial.print("\"mapped_filt_sigma_gyro_z\": ");
          Serial.print(-1.0 * mapped_filt_sigma_gyro_z);
          Serial.print(", ");
        }
        Serial.print("\"cf_heading\": ");
        Serial.print(rad2deg(cf_heading));
        Serial.print(", ");
        /*
        if (debug_rssi) {
          Serial.print("\"rssi\": ");
          Serial.print(rssi);
          Serial.print(", ");
        }
        Serial.print("\"distance\": ");
        Serial.print(dist);
        Serial.print(", ");
        */
        /*
        Serial.print("\"altitude\": ");
        Serial.print(alt);
        Serial.print(", ");
        */
        Serial.print("\"in_motion\": ");
        Serial.print(in_motion);
        Serial.print(", ");
        Serial.print("\"is_rotating\": ");
        Serial.print(is_rotating);
        Serial.println("}");
      }
    }
  }
}
