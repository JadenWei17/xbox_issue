// MPU6500 gyro integration and robot pose estimation.

float normalizeHeading(float h){ while(h>180)h-=360; while(h<=-180)h+=360; return h; }
bool readGyroZ(int16_t &z){
  if (Wire.getWireTimeoutFlag()) { Wire.clearWireTimeoutFlag(); return false; }
  Wire.beginTransmission(MPU_ADDRESS); Wire.write(0x47);
  if(Wire.endTransmission(false)!=0)return false;
  if(Wire.requestFrom(MPU_ADDRESS,(uint8_t)2)!=(uint8_t)2)return false;
  z=(int16_t)((Wire.read()<<8)|Wire.read()); return true;
}
void initializeMpu(){ Wire.begin(); Wire.setWireTimeout(I2C_TIMEOUT_US,true); Wire.beginTransmission(MPU_ADDRESS);Wire.write(0x6B);Wire.write(0);Wire.endTransmission(); delay(100); long sum=0;uint16_t n=0; for(uint16_t i=0;i<GYRO_CALIBRATION_SAMPLES;i++){int16_t z;if(readGyroZ(z)){sum+=z;n++;}delay(2);} gyroBias=n?(float)sum/n:0; lastMotionUs=lastMpuUpdateUs=micros(); }

void updateNavigation(){
  unsigned long now=micros(); if(now-lastMpuUpdateUs<MPU_UPDATE_INTERVAL_US)return;lastMpuUpdateUs=now;float dt=(now-lastMotionUs)*1e-6f; lastMotionUs=now; if(!(dt>0&&dt<0.5f))return;
  int16_t raw; if(readGyroZ(raw)){float w=((float)raw-gyroBias)/GYRO_SCALE;if(fabs(w)<GYRO_DEADBAND_DEG_S)w=0;pose.angularVelocityDegS=w;pose.headingTotalDeg+=w*dt;pose.headingDeg=normalizeHeading(pose.headingTotalDeg);}
  noInterrupts();unsigned long lc=leftEncoderCount,rc=rightEncoderCount;interrupts();
  int ls=lastLeftSpeed<0?-1:(lastLeftSpeed>0?1:0),rs=lastRightSpeed<0?-1:(lastRightSpeed>0?1:0);
  float dl=(float)(lc-previousLeftEncoderCount)*DISTANCE_PER_COUNT_CM*
      LINEAR_DISTANCE_SCALE*ls;
  float dr=(float)(rc-previousRightEncoderCount)*DISTANCE_PER_COUNT_CM*
      LINEAR_DISTANCE_SCALE*rs;
  previousLeftEncoderCount=lc;previousRightEncoderCount=rc;pose.leftDistanceCm+=dl;pose.rightDistanceCm+=dr;
  float dh=(pose.headingTotalDeg-previousHeadingTotalDeg)*DEG_TO_RAD,mid=(previousHeadingTotalDeg*DEG_TO_RAD)+0.5f*dh,ds=0.5f*(dl+dr);
  pose.xCm+=ds*cos(mid);pose.yCm+=ds*sin(mid);pose.linearVelocityCmS=ds/dt;
  previousLeftDistanceCm=pose.leftDistanceCm;previousRightDistanceCm=pose.rightDistanceCm;previousHeadingTotalDeg=pose.headingTotalDeg;
}

