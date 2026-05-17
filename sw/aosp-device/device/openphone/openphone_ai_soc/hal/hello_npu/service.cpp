// service.cpp - HwBinder service entry point for vendor.openphone.hello_npu@1.0.
//
// Single-threaded passthrough is sufficient for the v0 fixed-vector smoke
// RPC. Bumping the thread pool can wait for real workload evidence.

#define LOG_TAG "vendor.openphone.hello_npu@1.0-service"

#include <android-base/logging.h>
#include <hidl/HidlTransportSupport.h>

#include "HelloNpu.h"

using ::android::OK;
using ::android::sp;
using ::android::status_t;
using ::android::hardware::configureRpcThreadpool;
using ::android::hardware::joinRpcThreadpool;
using ::vendor::openphone::hello_npu::V1_0::IHelloNpu;
using ::vendor::openphone::hello_npu::V1_0::implementation::HelloNpu;

int main() {
    configureRpcThreadpool(1, true /* willJoin */);

    sp<IHelloNpu> service = new HelloNpu();
    status_t status = service->registerAsService();
    if (status != OK) {
        LOG(FATAL) << "Failed to register IHelloNpu/default: " << status;
        return 1;
    }

    LOG(INFO) << "vendor.openphone.hello_npu@1.0-service registered";
    joinRpcThreadpool();
    return 0;  // not reached
}
