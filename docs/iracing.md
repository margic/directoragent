# iRacing Telemetry Variables (Live Session)

This document provides a comprehensive, up-to-date list of iRacing telemetry variables available in a live session, as detected by the Sim RaceCenter connector. The table below is generated directly from the iRacing memory-mapped file, ensuring it reflects the current simulator version and car/track combination. Where possible, additional context is provided from official iRacing documentation and SDK reference files.

| Name | Type | Count | Unit | Description |
|------|------|-------|------|-------------|

| AirDensity | float | 1 | kg/m^3 | Density of air at start/finish line |
| AirPressure | float | 1 | Pa | Pressure of air at start/finish line |
| AirTemp | float | 1 | C | Temperature of air at start/finish line |
| Brake | float | 1 | % | 0=brake released to 1=max pedal force |
| BrakeABSactive | bool | 1 |  | true if abs is currently reducing brake force pressure |
| BrakeRaw | float | 1 | % | Raw brake input 0=brake released to 1=max pedal force |
| CamCameraNumber | int | 1 |  | Active camera number |
| CamCameraState | bitfield | 1 | irsdk_CameraState | State of camera system |
| CamCarIdx | int | 1 |  | Active camera's focus car index |
| CamGroupNumber | int | 1 |  | Active camera group number |
| CarDistAhead | float | 1 | m | Distance to first car in front of player in meters |
| CarDistBehind | float | 1 | m | Distance to first car behind player in meters |
| CarIdxBestLapNum | int | 64 |  | Cars best lap number |
| CarIdxBestLapTime | float | 64 | s | Cars best lap time |
| CarIdxClass | int | 64 |  | Cars class id by car index |
| CarIdxClassPosition | int | 64 |  | Cars class position in race by car index |
| CarIdxEstTime | float | 64 | s | Estimated time to reach current location on track |
| CarIdxF2Time | float | 64 | s | Race time behind leader or fastest lap time otherwise |
| CarIdxFastRepairsUsed | int | 64 |  | How many fast repairs each car has used |
| CarIdxGear | int | 64 |  | -1=reverse  0=neutral  1..n=current gear by car index |
| CarIdxLap | int | 64 |  | Laps started by car index |
| CarIdxLapCompleted | int | 64 |  | Laps completed by car index |
| CarIdxLapDistPct | float | 64 | % | Percentage distance around lap by car index |
| CarIdxLastLapTime | float | 64 | s | Cars last lap time |
| CarIdxOnPitRoad | bool | 64 |  | On pit road between the cones by car index |
| CarIdxP2P_Count | int | 64 |  | Push2Pass count of usage (or remaining in Race) |
| CarIdxP2P_Status | bool | 64 |  | Push2Pass active or not |
| CarIdxPaceFlags | bitfield | 64 | irsdk_PaceFlags | Pacing status flags for each car |
| CarIdxPaceLine | int | 64 |  | What line cars are pacing in  or -1 if not pacing |
| CarIdxPaceRow | int | 64 |  | What row cars are pacing in  or -1 if not pacing |
| CarIdxPosition | int | 64 |  | Cars position in race by car index |
| CarIdxQualTireCompound | int | 64 |  | Cars Qual tire compound |
| CarIdxQualTireCompoundLocked | bool | 64 |  | Cars Qual tire compound is locked-in |
| CarIdxRPM | float | 64 | revs/min | Engine rpm by car index |
| CarIdxSessionFlags | bitfield | 64 | irsdk_Flags | Session flags for each player |
| CarIdxSteer | float | 64 | rad | Steering wheel angle by car index |
| CarIdxTireCompound | int | 64 |  | Cars current tire compound |
| CarIdxTrackSurface | int | 64 | irsdk_TrkLoc | Track surface type by car index |
| CarIdxTrackSurfaceMaterial | int | 64 | irsdk_TrkSurf | Track surface material type by car index |
| CarLeftRight | int | 1 | irsdk_CarLeftRight | Notify if car is to the left or right of driver |
| ChanAvgLatency | float | 1 | s | Communications average latency |
| ChanClockSkew | float | 1 | s | Communications server clock skew |
| ChanLatency | float | 1 | s | Communications latency |
| ChanPartnerQuality | float | 1 | % | Partner communications quality |
| ChanQuality | float | 1 | % | Communications quality |
| Clutch | float | 1 | % | 0=disengaged to 1=fully engaged |
| ClutchRaw | float | 1 | % | Raw clutch input 0=disengaged to 1=fully engaged |
| CpuUsageBG | float | 1 | % | Percent of available tim bg thread took with a 1 sec avg |
| CpuUsageFG | float | 1 | % | Percent of available tim fg thread took with a 1 sec avg |
| DCDriversSoFar | int | 1 |  | Number of team drivers who have run a stint |
| DCLapStatus | int | 1 |  | Status of driver change lap requirements |
| DisplayUnits | int | 1 |  | Default units for the user interface 0 = english 1 = metric |
| DriverMarker | bool | 1 |  | Driver activated flag |
| Engine0_RPM | float | 1 | revs/min | Engine0Engine rpm |
| EngineWarnings | bitfield | 1 | irsdk_EngineWarnings | Bitfield for warning lights |
| EnterExitReset | int | 1 |  | Indicate action the reset key will take 0 enter 1 exit 2 reset |
| FastRepairAvailable | int | 1 |  | How many fast repairs left  255 is unlimited |
| FastRepairUsed | int | 1 |  | How many fast repairs used so far |
| FogLevel | float | 1 | % | Fog level at start/finish line |
| FrameRate | float | 1 | fps | Average frames per second |
| FrontTireSetsAvailable | int | 1 |  | How many front tire sets are remaining  255 is unlimited |
| FrontTireSetsUsed | int | 1 |  | How many front tire sets used so far |
| FuelLevel | float | 1 | l | Liters of fuel remaining |
| FuelLevelPct | float | 1 | % | Percent fuel remaining |
| FuelPress | float | 1 | bar | Engine fuel pressure |
| FuelUsePerHour | float | 1 | kg/h | Engine fuel used instantaneous |
| Gear | int | 1 |  | -1=reverse  0=neutral  1..n=current gear |
| GpuUsage | float | 1 | % | Percent of available tim gpu took with a 1 sec avg |
| HandbrakeRaw | float | 1 | % | Raw handbrake input 0=handbrake released to 1=max force |
| IsDiskLoggingActive | bool | 1 |  | 0=disk based telemetry file not being written  1=being written |
| IsDiskLoggingEnabled | bool | 1 |  | 0=disk based telemetry turned off  1=turned on |
| IsGarageVisible | bool | 1 |  | 1=Garage screen is visible |
| IsInGarage | bool | 1 |  | 1=Car in garage physics running |
| IsOnTrack | bool | 1 |  | 1=Car on track physics running with player in car |
| IsOnTrackCar | bool | 1 |  | 1=Car on track physics running |
| IsReplayPlaying | bool | 1 |  | 0=replay not playing  1=replay playing |
| LFTiresAvailable | int | 1 |  | How many left front tires are remaining  255 is unlimited |
| LFTiresUsed | int | 1 |  | How many left front tires used so far |
| LFbrakeLinePress | float | 1 | bar | LF brake line pressure |
| LFcoldPressure | float | 1 | kPa | LF tire cold pressure  as set in the garage |
| LFshockDefl | float | 1 | m | LF shock deflection |
| LFshockDefl_ST | float | 6 | m | LF shock deflection at 360 Hz |
| LFshockVel | float | 1 | m/s | LF shock velocity |
| LFshockVel_ST | float | 6 | m/s | LF shock velocity at 360 Hz |
| LFtempCL | float | 1 | C | LF tire left carcass temperature |
| LFtempCM | float | 1 | C | LF tire middle carcass temperature |
| LFtempCR | float | 1 | C | LF tire right carcass temperature |
| LFwearL | float | 1 | % | LF tire left percent tread remaining |
| LFwearM | float | 1 | % | LF tire middle percent tread remaining |
| LFwearR | float | 1 | % | LF tire right percent tread remaining |
| LRTiresAvailable | int | 1 |  | How many left rear tires are remaining  255 is unlimited |
| LRTiresUsed | int | 1 |  | How many left rear tires used so far |
| LRbrakeLinePress | float | 1 | bar | LR brake line pressure |
| LRcoldPressure | float | 1 | kPa | LR tire cold pressure  as set in the garage |
| LRshockDefl | float | 1 | m | LR shock deflection |
| LRshockDefl_ST | float | 6 | m | LR shock deflection at 360 Hz |
| LRshockVel | float | 1 | m/s | LR shock velocity |
| LRshockVel_ST | float | 6 | m/s | LR shock velocity at 360 Hz |
| LRtempCL | float | 1 | C | LR tire left carcass temperature |
| LRtempCM | float | 1 | C | LR tire middle carcass temperature |
| LRtempCR | float | 1 | C | LR tire right carcass temperature |
| LRwearL | float | 1 | % | LR tire left percent tread remaining |
| LRwearM | float | 1 | % | LR tire middle percent tread remaining |
| LRwearR | float | 1 | % | LR tire right percent tread remaining |
| Lap | int | 1 |  | Laps started count |
| LapBestLap | int | 1 |  | Players best lap number |
| LapBestLapTime | float | 1 | s | Players best lap time |
| LapBestNLapLap | int | 1 |  | Player last lap in best N average lap time |
| LapBestNLapTime | float | 1 | s | Player best N average lap time |
| LapCompleted | int | 1 |  | Laps completed count |
| LapCurrentLapTime | float | 1 | s | Estimate of players current lap time as shown in F3 box |
| LapDeltaToBestLap | float | 1 | s | Delta time for best lap |
| LapDeltaToBestLap_DD | float | 1 | s/s | Rate of change of delta time for best lap |
| LapDeltaToBestLap_OK | bool | 1 |  | Delta time for best lap is valid |
| LapDeltaToOptimalLap | float | 1 | s | Delta time for optimal lap |
| LapDeltaToOptimalLap_DD | float | 1 | s/s | Rate of change of delta time for optimal lap |
| LapDeltaToOptimalLap_OK | bool | 1 |  | Delta time for optimal lap is valid |
| LapDeltaToSessionBestLap | float | 1 | s | Delta time for session best lap |
| LapDeltaToSessionBestLap_DD | float | 1 | s/s | Rate of change of delta time for session best lap |
| LapDeltaToSessionBestLap_OK | bool | 1 |  | Delta time for session best lap is valid |
| LapDeltaToSessionLastlLap | float | 1 | s | Delta time for session last lap |
| LapDeltaToSessionLastlLap_DD | float | 1 | s/s | Rate of change of delta time for session last lap |
| LapDeltaToSessionLastlLap_OK | bool | 1 |  | Delta time for session last lap is valid |
| LapDeltaToSessionOptimalLap | float | 1 | s | Delta time for session optimal lap |
| LapDeltaToSessionOptimalLap_DD | float | 1 | s/s | Rate of change of delta time for session optimal lap |
| LapDeltaToSessionOptimalLap_OK | bool | 1 |  | Delta time for session optimal lap is valid |
| LapDist | float | 1 | m | Meters traveled from S/F this lap |
| LapDistPct | float | 1 | % | Percentage distance around lap |
| LapLasNLapSeq | int | 1 |  | Player num consecutive clean laps completed for N average |
| LapLastLapTime | float | 1 | s | Players last lap time |
| LapLastNLapTime | float | 1 | s | Player last N average lap time |
| LatAccel | float | 1 | m/s^2 | Lateral acceleration (including gravity) |
| LatAccel_ST | float | 6 | m/s^2 | Lateral acceleration (including gravity) at 360 Hz |
| LeftTireSetsAvailable | int | 1 |  | How many left tire sets are remaining  255 is unlimited |
| LeftTireSetsUsed | int | 1 |  | How many left tire sets used so far |
| LoadNumTextures | bool | 1 |  | True if the car_num texture will be loaded |
| LongAccel | float | 1 | m/s^2 | Longitudinal acceleration (including gravity) |
| LongAccel_ST | float | 6 | m/s^2 | Longitudinal acceleration (including gravity) at 360 Hz |
| ManifoldPress | float | 1 | bar | Engine manifold pressure |
| ManualBoost | bool | 1 |  | Hybrid manual boost state |
| ManualNoBoost | bool | 1 |  | Hybrid manual no boost state |
| MemPageFaultSec | float | 1 |  | Memory page faults per second |
| MemSoftPageFaultSec | float | 1 |  | Memory soft page faults per second |
| OilLevel | float | 1 | l | Engine oil level |
| OilPress | float | 1 | bar | Engine oil pressure |
| OilTemp | float | 1 | C | Engine oil temperature |
| OkToReloadTextures | bool | 1 |  | True if it is ok to reload car textures at this time |
| OnPitRoad | bool | 1 |  | Is the player car on pit road between the cones |
| P2P_Count | int | 1 |  | Push2Pass count of usage (or remaining in Race) on your car |
| P2P_Status | bool | 1 |  | Push2Pass active or not on your car |
| PaceMode | int | 1 | irsdk_PaceMode | Are we pacing or not |
| PitOptRepairLeft | float | 1 | s | Time left for optional repairs if repairs are active |
| PitRepairLeft | float | 1 | s | Time left for mandatory pit repairs if repairs are active |
| PitSvFlags | bitfield | 1 | irsdk_PitSvFlags | Bitfield of pit service checkboxes |
| PitSvFuel | float | 1 | l or kWh | Pit service fuel add amount |
| PitSvLFP | float | 1 | kPa | Pit service left front tire pressure |
| PitSvLRP | float | 1 | kPa | Pit service left rear tire pressure |
| PitSvRFP | float | 1 | kPa | Pit service right front tire pressure |
| PitSvRRP | float | 1 | kPa | Pit service right rear tire pressure |
| PitSvTireCompound | int | 1 |  | Pit service pending tire compound |
| Pitch | float | 1 | rad | Pitch orientation |
| PitchRate | float | 1 | rad/s | Pitch rate |
| PitchRate_ST | float | 6 | rad/s | Pitch rate at 360 Hz |
| PitsOpen | bool | 1 |  | True if pit stop is allowed for the current player |
| PitstopActive | bool | 1 |  | Is the player getting pit stop service |
| PlayerCarClass | int | 1 |  | Player car class id |
| PlayerCarClassPosition | int | 1 |  | Players class position in race |
| PlayerCarDriverIncidentCount | int | 1 |  | Teams current drivers incident count for this session |
| PlayerCarDryTireSetLimit | int | 1 |  | Players dry tire set limit |
| PlayerCarIdx | int | 1 |  | Players carIdx |
| PlayerCarInPitStall | bool | 1 |  | Players car is properly in their pitstall |
| PlayerCarMyIncidentCount | int | 1 |  | Players own incident count for this session |
| PlayerCarPitSvStatus | int | 1 | irsdk_PitSvStatus | Players car pit service status bits |
| PlayerCarPosition | int | 1 |  | Players position in race |
| PlayerCarPowerAdjust | float | 1 | % | Players power adjust |
| PlayerCarSLBlinkRPM | float | 1 | revs/min | Shift light blink rpm |
| PlayerCarSLFirstRPM | float | 1 | revs/min | Shift light first light rpm |
| PlayerCarSLLastRPM | float | 1 | revs/min | Shift light last light rpm |
| PlayerCarSLShiftRPM | float | 1 | revs/min | Shift light shift rpm |
| PlayerCarTeamIncidentCount | int | 1 |  | Players team incident count for this session |
| PlayerCarTowTime | float | 1 | s | Players car is being towed if time is greater than zero |
| PlayerCarWeightPenalty | float | 1 | kg | Players weight penalty |
| PlayerFastRepairsUsed | int | 1 |  | Players car number of fast repairs used |
| PlayerTireCompound | int | 1 |  | Players car current tire compound |
| PlayerTrackSurface | int | 1 | irsdk_TrkLoc | Players car track surface type |
| PlayerTrackSurfaceMaterial | int | 1 | irsdk_TrkSurf | Players car track surface material type |
| Precipitation | float | 1 | % | Precipitation at start/finish line |
| PushToPass | bool | 1 |  | Push to pass button state |
| PushToTalk | bool | 1 |  | Push to talk button state |
| RFTiresAvailable | int | 1 |  | How many right front tires are remaining  255 is unlimited |
| RFTiresUsed | int | 1 |  | How many right front tires used so far |
| RFbrakeLinePress | float | 1 | bar | RF brake line pressure |
| RFcoldPressure | float | 1 | kPa | RF tire cold pressure  as set in the garage |
| RFshockDefl | float | 1 | m | RF shock deflection |
| RFshockDefl_ST | float | 6 | m | RF shock deflection at 360 Hz |
| RFshockVel | float | 1 | m/s | RF shock velocity |
| RFshockVel_ST | float | 6 | m/s | RF shock velocity at 360 Hz |
| RFtempCL | float | 1 | C | RF tire left carcass temperature |
| RFtempCM | float | 1 | C | RF tire middle carcass temperature |
| RFtempCR | float | 1 | C | RF tire right carcass temperature |
| RFwearL | float | 1 | % | RF tire left percent tread remaining |
| RFwearM | float | 1 | % | RF tire middle percent tread remaining |
| RFwearR | float | 1 | % | RF tire right percent tread remaining |
| RPM | float | 1 | revs/min | Engine rpm |
| RRTiresAvailable | int | 1 |  | How many right rear tires are remaining  255 is unlimited |
| RRTiresUsed | int | 1 |  | How many right rear tires used so far |
| RRbrakeLinePress | float | 1 | bar | RR brake line pressure |
| RRcoldPressure | float | 1 | kPa | RR tire cold pressure  as set in the garage |
| RRshockDefl | float | 1 | m | RR shock deflection |
| RRshockDefl_ST | float | 6 | m | RR shock deflection at 360 Hz |
| RRshockVel | float | 1 | m/s | RR shock velocity |
| RRshockVel_ST | float | 6 | m/s | RR shock velocity at 360 Hz |
| RRtempCL | float | 1 | C | RR tire left carcass temperature |
| RRtempCM | float | 1 | C | RR tire middle carcass temperature |
| RRtempCR | float | 1 | C | RR tire right carcass temperature |
| RRwearL | float | 1 | % | RR tire left percent tread remaining |
| RRwearM | float | 1 | % | RR tire middle percent tread remaining |
| RRwearR | float | 1 | % | RR tire right percent tread remaining |
| RaceLaps | int | 1 |  | Laps completed in race |
| RadioTransmitCarIdx | int | 1 |  | The car index of the current person speaking on the radio |
| RadioTransmitFrequencyIdx | int | 1 |  | The frequency index of the current person speaking on the radio |
| RadioTransmitRadioIdx | int | 1 |  | The radio index of the current person speaking on the radio |
| RearTireSetsAvailable | int | 1 |  | How many rear tire sets are remaining  255 is unlimited |
| RearTireSetsUsed | int | 1 |  | How many rear tire sets used so far |
| RelativeHumidity | float | 1 | % | Relative Humidity at start/finish line |
| ReplayFrameNum | int | 1 |  | Integer replay frame number (60 per second) |
| ReplayFrameNumEnd | int | 1 |  | Integer replay frame number from end of tape |
| ReplayPlaySlowMotion | bool | 1 |  | 0=not slow motion  1=replay is in slow motion |
| ReplayPlaySpeed | int | 1 |  | Replay playback speed |
| ReplaySessionNum | int | 1 |  | Replay session number |
| ReplaySessionTime | double | 1 | s | Seconds since replay session start |
| RightTireSetsAvailable | int | 1 |  | How many right tire sets are remaining  255 is unlimited |
| RightTireSetsUsed | int | 1 |  | How many right tire sets used so far |
| Roll | float | 1 | rad | Roll orientation |
| RollRate | float | 1 | rad/s | Roll rate |
| RollRate_ST | float | 6 | rad/s | Roll rate at 360 Hz |
| SessionFlags | bitfield | 1 | irsdk_Flags | Session flags |
| SessionJokerLapsRemain | int | 1 |  | Joker laps remaining to be taken |
| SessionLapsRemain | int | 1 |  | Old laps left till session ends use SessionLapsRemainEx |
| SessionLapsRemainEx | int | 1 |  | New improved laps left till session ends |
| SessionLapsTotal | int | 1 |  | Total number of laps in session |
| SessionNum | int | 1 |  | Session number |
| SessionOnJokerLap | bool | 1 |  | Player is currently completing a joker lap |
| SessionState | int | 1 | irsdk_SessionState | Session state |
| SessionTick | int | 1 |  | Current update number |
| SessionTime | double | 1 | s | Seconds since session start |
| SessionTimeOfDay | float | 1 | s | Time of day in seconds |
| SessionTimeRemain | double | 1 | s | Seconds left till session ends |
| SessionTimeTotal | double | 1 | s | Total number of seconds in session |
| SessionUniqueID | int | 1 |  | Session ID |
| ShiftGrindRPM | float | 1 | RPM | RPM of shifter grinding noise |
| ShiftIndicatorPct | float | 1 | % | DEPRECATED use DriverCarSLBlinkRPM instead |
| ShiftPowerPct | float | 1 | % | Friction torque applied to gears when shifting or grinding |
| Skies | int | 1 |  | Skies (0=clear/1=p cloudy/2=m cloudy/3=overcast) |
| SolarAltitude | float | 1 | rad | Sun angle above horizon in radians |
| SolarAzimuth | float | 1 | rad | Sun angle clockwise from north in radians |
| Speed | float | 1 | m/s | GPS vehicle speed |
| SteeringFFBEnabled | bool | 1 |  | Force feedback is enabled |
| SteeringWheelAngle | float | 1 | rad | Steering wheel angle |
| SteeringWheelAngleMax | float | 1 | rad | Steering wheel max angle |
| SteeringWheelLimiter | float | 1 | % | Force feedback limiter strength limits impacts and oscillation |
| SteeringWheelMaxForceNm | float | 1 | N*m | Value of strength or max force slider in Nm for FFB |
| SteeringWheelPctDamper | float | 1 | % | Force feedback % max damping |
| SteeringWheelPctIntensity | float | 1 | % | Force feedback % max intensity |
| SteeringWheelPctSmoothing | float | 1 | % | Force feedback % max smoothing |
| SteeringWheelPctTorque | float | 1 | % | Force feedback % max torque on steering shaft unsigned |
| SteeringWheelPctTorqueSign | float | 1 | % | Force feedback % max torque on steering shaft signed |
| SteeringWheelPctTorqueSignStops | float | 1 | % | Force feedback % max torque on steering shaft signed stops |
| SteeringWheelPeakForceNm | float | 1 | N*m | Peak torque mapping to direct input units for FFB |
| SteeringWheelTorque | float | 1 | N*m | Output torque on steering shaft |
| SteeringWheelTorque_ST | float | 6 | N*m | Output torque on steering shaft at 360 Hz |
| SteeringWheelUseLinear | bool | 1 |  | True if steering wheel force is using linear mode |
| Throttle | float | 1 | % | 0=off throttle to 1=full throttle |
| ThrottleRaw | float | 1 | % | Raw throttle input 0=off throttle to 1=full throttle |
| TireLF_RumblePitch | float | 1 | Hz | Players LF Tire Sound rumblestrip pitch |
| TireLR_RumblePitch | float | 1 | Hz | Players LR Tire Sound rumblestrip pitch |
| TireRF_RumblePitch | float | 1 | Hz | Players RF Tire Sound rumblestrip pitch |
| TireRR_RumblePitch | float | 1 | Hz | Players RR Tire Sound rumblestrip pitch |
| TireSetsAvailable | int | 1 |  | How many tire sets are remaining  255 is unlimited |
| TireSetsUsed | int | 1 |  | How many tire sets used so far |
| TrackTemp | float | 1 | C | Deprecated  set to TrackTempCrew |
| TrackTempCrew | float | 1 | C | Temperature of track measured by crew around track |
| TrackWetness | int | 1 | irsdk_TrackWetness | How wet is the average track surface |
| VelocityX | float | 1 | m/s | X velocity |
| VelocityX_ST | float | 6 | m/s at 360 Hz | X velocity |
| VelocityY | float | 1 | m/s | Y velocity |
| VelocityY_ST | float | 6 | m/s at 360 Hz | Y velocity |
| VelocityZ | float | 1 | m/s | Z velocity |
| VelocityZ_ST | float | 6 | m/s at 360 Hz | Z velocity |
| VertAccel | float | 1 | m/s^2 | Vertical acceleration (including gravity) |
| VertAccel_ST | float | 6 | m/s^2 | Vertical acceleration (including gravity) at 360 Hz |
| VidCapActive | bool | 1 |  | True if video currently being captured |
| VidCapEnabled | bool | 1 |  | True if video capture system is enabled |
| Voltage | float | 1 | V | Engine voltage |
| WaterLevel | float | 1 | l | Engine coolant level |
| WaterTemp | float | 1 | C | Engine coolant temp |
| WeatherDeclaredWet | bool | 1 |  | The steward says rain tires can be used |
| WindDir | float | 1 | rad | Wind direction at start/finish line |
| WindVel | float | 1 | m/s | Wind velocity at start/finish line |
| Yaw | float | 1 | rad | Yaw orientation |
| YawNorth | float | 1 | rad | Yaw orientation relative to north |
| YawRate | float | 1 | rad/s | Yaw rate |
| YawRate_ST | float | 6 | rad/s | Yaw rate at 360 Hz |
| dcBrakeBias | float | 1 |  | In car brake bias adjustment |
| dcHeadlightFlash | bool | 1 |  | In car headlight flash control active |
| dcPitSpeedLimiterToggle | bool | 1 |  | Track if pit speed limiter system is enabled |
| dcStarter | bool | 1 |  | In car trigger car starter |
| dcThrottleShape | float | 1 |  | In car throttle shape adjustment |
| dcToggleWindshieldWipers | bool | 1 |  | In car turn wipers on or off |
| dcTractionControl | float | 1 |  | In car traction control adjustment |
| dcTriggerWindshieldWipers | bool | 1 |  | In car momentarily turn on wipers |
| dpFastRepair | float | 1 |  | Pitstop fast repair set |
| dpFuelAddKg | float | 1 | kg | Pitstop fuel add amount |
| dpFuelAutoFillActive | float | 1 |  | Pitstop auto fill fuel next stop flag |
| dpFuelAutoFillEnabled | float | 1 |  | Pitstop auto fill fuel system enabled |
| dpFuelFill | float | 1 |  | Pitstop fuel fill flag |
| dpLFTireChange | float | 1 |  | Pitstop lf tire change request |
| dpLFTireColdPress | float | 1 | Pa | Pitstop lf tire cold pressure adjustment |
| dpLRTireChange | float | 1 |  | Pitstop lr tire change request |
| dpLRTireColdPress | float | 1 | Pa | Pitstop lr tire cold pressure adjustment |
| dpRFTireChange | float | 1 |  | Pitstop rf tire change request |
| dpRFTireColdPress | float | 1 | Pa | Pitstop rf cold tire pressure adjustment |
| dpRRTireChange | float | 1 |  | Pitstop rr tire change request |
| dpRRTireColdPress | float | 1 | Pa | Pitstop rr cold tire pressure adjustment |
| dpWindshieldTearoff | float | 1 |  | Pitstop windshield tearoff |


---

## Reference: Special Types and Bitfields

<details>
<summary><strong>irsdk_TrkLoc</strong> (Track Location)</summary>

| Value | Meaning |
|-------|---------|
| -1 | Not in world |
| 0 | Off track |
| 1 | In pit stall |
| 2 | Approaching pits |
| 3 | On track |

</details>

<details>
<summary><strong>irsdk_TrkSurf</strong> (Track Surface Material)</summary>

| Value | Material |
|-------|----------|
| -1 | Not in world |
| 0 | Undefined |
| 1 | Asphalt1 |
| 2 | Asphalt2 |
| 3 | Asphalt3 |
| 4 | Asphalt4 |
| 5 | Concrete1 |
| 6 | Concrete2 |
| 7 | RacingDirt1 |
| 8 | RacingDirt2 |
| 9 | Paint1 |
| 10 | Paint2 |
| 11 | Rumble1 |
| 12 | Rumble2 |
| 13 | Rumble3 |
| 14 | Rumble4 |
| 15 | Grass1 |
| 16 | Grass2 |
| 17 | Grass3 |
| 18 | Grass4 |
| 19 | Dirt1 |
| 20 | Dirt2 |
| 21 | Dirt3 |
| 22 | Dirt4 |
| 23 | Sand |
| 24 | Gravel1 |
| 25 | Gravel2 |
| 26 | Grasscrete |
| 27 | Astroturf |

</details>

<details>
<summary><strong>irsdk_Flags</strong> (Session Flags, CarIdxSessionFlags, etc.)</summary>

Bitfield (can be combined):

| Flag | Value | Description |
|------|-------|-------------|
| irsdk_checkered | 0x00000001 | Checkered flag |
| irsdk_white | 0x00000002 | White flag |
| irsdk_green | 0x00000004 | Green flag |
| irsdk_yellow | 0x00000008 | Yellow flag |
| irsdk_red | 0x00000010 | Red flag |
| irsdk_blue | 0x00000020 | Blue flag |
| irsdk_debris | 0x00000040 | Debris flag |
| irsdk_crossed | 0x00000080 | Crossed flag |
| irsdk_yellowWaving | 0x00000100 | Waving yellow |
| irsdk_oneLapToGreen | 0x00000200 | One lap to green |
| irsdk_greenHeld | 0x00000400 | Green held |
| irsdk_tenToGo | 0x00000800 | Ten to go |
| irsdk_fiveToGo | 0x00001000 | Five to go |
| irsdk_randomWaving | 0x00002000 | Random waving |
| irsdk_caution | 0x00004000 | Caution |
| irsdk_cautionWaving | 0x00008000 | Caution waving |
| irsdk_black | 0x00010000 | Black flag |
| irsdk_disqualify | 0x00020000 | Disqualify |
| irsdk_servicible | 0x00040000 | Car is allowed service |
| irsdk_furled | 0x00080000 | Furled |
| irsdk_repair | 0x00100000 | Repair |
| irsdk_startHidden | 0x10000000 | Start hidden |
| irsdk_startReady | 0x20000000 | Start ready |
| irsdk_startSet | 0x40000000 | Start set |
| irsdk_startGo | 0x80000000 | Start go |

</details>

<details>
<summary><strong>irsdk_CameraState</strong></summary>

Bitfield (can be combined):

| Flag | Value | Description |
|------|-------|-------------|
| irsdk_IsSessionScreen | 0x0001 | Camera tool can only be activated if viewing the session screen |
| irsdk_IsScenicActive | 0x0002 | Scenic camera is active |
| irsdk_CamToolActive | 0x0004 | Camera tool active |
| irsdk_UIHidden | 0x0008 | UI hidden |
| irsdk_UseAutoShotSelection | 0x0010 | Auto shot selection |
| irsdk_UseTemporaryEdits | 0x0020 | Temporary edits |
| irsdk_UseKeyAcceleration | 0x0040 | Key acceleration |
| irsdk_UseKey10xAcceleration | 0x0080 | 10x key acceleration |
| irsdk_UseMouseAimMode | 0x0100 | Mouse aim mode |

</details>

<details>
<summary><strong>irsdk_EngineWarnings</strong></summary>

Bitfield (can be combined):

| Flag | Value | Description |
|------|-------|-------------|
| irsdk_waterTempWarning | 0x0001 | Water temp warning |
| irsdk_fuelPressureWarning | 0x0002 | Fuel pressure warning |
| irsdk_oilPressureWarning | 0x0004 | Oil pressure warning |
| irsdk_engineStalled | 0x0008 | Engine stalled |
| irsdk_pitSpeedLimiter | 0x0010 | Pit speed limiter |
| irsdk_revLimiterActive | 0x0020 | Rev limiter active |
| irsdk_oilTempWarning | 0x0040 | Oil temp warning |

</details>

<details>
<summary><strong>irsdk_PitSvFlags</strong></summary>

Bitfield (can be combined):

| Flag | Value | Description |
|------|-------|-------------|
| irsdk_LFTireChange | 0x0001 | Left front tire change |
| irsdk_RFTireChange | 0x0002 | Right front tire change |
| irsdk_LRTireChange | 0x0004 | Left rear tire change |
| irsdk_RRTireChange | 0x0008 | Right rear tire change |
| irsdk_FuelFill | 0x0010 | Fuel fill |
| irsdk_WindshieldTearoff | 0x0020 | Windshield tearoff |
| irsdk_FastRepair | 0x0040 | Fast repair |

</details>

<details>
<summary><strong>irsdk_PaceFlags</strong></summary>

Bitfield (can be combined):

| Flag | Value | Description |
|------|-------|-------------|
| irsdk_PaceFlagsEndOfLine | 0x0001 | End of line |
| irsdk_PaceFlagsFreePass | 0x0002 | Free pass |
| irsdk_PaceFlagsWavedAround | 0x0004 | Waved around |

</details>

<details>
<summary><strong>irsdk_CarLeftRight</strong></summary>

| Value | Meaning |
|-------|---------|
| 0 | Off |
| 1 | Clear |
| 2 | Car left |
| 3 | Car right |
| 4 | Car left and right |
| 5 | Two cars left |
| 6 | Two cars right |

</details>

<details>
<summary><strong>irsdk_PitSvStatus</strong></summary>

| Value | Meaning |
|-------|---------|
| 0 | None |
| 1 | In progress |
| 2 | Complete |
| 100 | Too far left |
| 101 | Too far right |
| 102 | Too far forward |
| 103 | Too far back |
| 104 | Bad angle |
| 105 | Can't fix that |

</details>

<details>
<summary><strong>irsdk_PaceMode</strong></summary>

| Value | Meaning |
|-------|---------|
| 0 | Single file start |
| 1 | Double file start |
| 2 | Single file restart |
| 3 | Double file restart |
| 4 | Not pacing |

</details>

<details>
<summary><strong>irsdk_SessionState</strong></summary>

| Value | Meaning |
|-------|---------|
| 0 | Invalid |
| 1 | Get in car |
| 2 | Warmup |
| 3 | Parade laps |
| 4 | Racing |
| 5 | Checkered |
| 6 | Cool down |

</details>

<details>
<summary><strong>irsdk_WeatherDynamics</strong></summary>

| Value | Meaning |
|-------|---------|
| 0 | Specified, fixed sky |
| 1 | Generated, sky moves |
| 2 | Generated, fixed sky |
| 3 | Specified, sky moves |

</details>

<details>
<summary><strong>irsdk_WeatherVersion</strong></summary>

| Value | Meaning |
|-------|---------|
| 0 | Classic (no rain) |
| 1 | Forecast-based |
| 2 | Static test day (W2, track water) |
| 3 | Timeline-based |

</details>
