# Torque coordination HLD — synthetic development fixture

The EngineControl component provides the TorqueInterface interface to the InstrumentCluster component.
The TorqueInterface interface carries the Torque signal.
The Torque signal has type uint16 and unit Nm.
The EngineControl component provides the TorqueInterface interface through port TorqueOut.
The InstrumentCluster component requires the TorqueInterface interface through port TorqueIn.
The TorqueDelivery flow runs from the EngineControl component to the InstrumentCluster component.
