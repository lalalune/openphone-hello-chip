// SPDX-License-Identifier: Apache-2.0
#ifndef OPENPHONE_HELLO_NPU_RUNTIME_H_
#define OPENPHONE_HELLO_NPU_RUNTIME_H_

#include <string>

namespace openphone {
namespace hello_npu {

struct ProbeResult {
	bool device_node_present;
	bool runtime_supported;
	bool nnapi_acceleration;
	int open_errno;
	std::string status;
	std::string reason;
};

ProbeResult ProbeDevice(const std::string &device_path);
std::string FormatProbeResult(const std::string &device_path, const ProbeResult &result);

}  // namespace hello_npu
}  // namespace openphone

#endif  // OPENPHONE_HELLO_NPU_RUNTIME_H_
