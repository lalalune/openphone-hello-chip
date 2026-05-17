// HelloNpu.h - v0 stub implementation for vendor.openphone.hello_npu@1.0.
//
// Backing contract: sw/platform/hello_platform_contract.json
// Backing kernel node: /dev/hello-npu
//
// Fail-closed semantics:
//   - Constructor records whether /dev/hello-npu can be opened. It does
//     NOT keep the fd long-term; the smoke RPC re-opens on demand so a
//     hot-unplug or kernel module reload is handled without state.
//   - All RPCs return Status::NOT_SUPPORTED when the device node is
//     missing. Any partial read or ioctl failure returns IO_ERROR.

#pragma once

#include <sys/types.h>
#include <vendor/openphone/hello_npu/1.0/IHelloNpu.h>

namespace vendor {
namespace openphone {
namespace hello_npu {
namespace V1_0 {
namespace implementation {

class HelloNpu : public IHelloNpu {
public:
    HelloNpu();

    // IHelloNpu
    ::android::hardware::Return<void> smoke(smoke_cb _hidl_cb) override;

private:
    // Path to the backing char device. Never cached as an fd.
    static constexpr const char* kDevicePath = "/dev/hello-npu";

    // Offset into the device that returns the driver identity word.
    // Matches sw/linux/drivers/hello/hello_platform_contract.h
    // (HELLO_NPU_RESULT_OFFSET).
    static constexpr off_t kResultOffset = 0x10;
};

}  // namespace implementation
}  // namespace V1_0
}  // namespace hello_npu
}  // namespace openphone
}  // namespace vendor
