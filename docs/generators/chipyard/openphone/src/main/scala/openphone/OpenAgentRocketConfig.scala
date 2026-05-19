package openagent

import org.chipsalliance.cde.config.Config

class OpenAgentRocketConfig extends Config(
  new chipyard.harness.WithBlockDeviceModel ++
  new testchipip.iceblk.WithBlockDevice ++
  new chipyard.config.WithPeripheryTimer ++
  new freechips.rocketchip.rocket.WithNHugeCores(1) ++
  new chipyard.config.AbstractConfig)
