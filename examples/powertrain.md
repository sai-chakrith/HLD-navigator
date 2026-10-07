# Powertrain HLD — synthetic example
This document is a hand-authored software fixture, not an OEM HLD.

## Components
Component: SpeedEstimator | description=Computes vehicle speed
Component: InstrumentCluster | description=Displays vehicle speed

## Interfaces and signals
Signal: VehicleSpeed | type=uint16 | unit=km/h
Interface: VehicleSpeedInterface | kind=sender_receiver | payload=VehicleSpeed

## Ports and dependencies
Port: SpeedOut | owner=SpeedEstimator | interface=VehicleSpeedInterface | direction=provides
Port: SpeedIn | owner=InstrumentCluster | interface=VehicleSpeedInterface | direction=requires
Dependency: SpeedDisplay | source=SpeedEstimator | target=InstrumentCluster | interface=VehicleSpeedInterface
Flow: DisplaySpeed | source=SpeedEstimator | target=InstrumentCluster | description=Speed estimate feeds display
