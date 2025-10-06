// Minimal RoastLink TWO (ESP32-S3) flasher build

// Core imports
import { Transport } from "./webserial.js";
import { ESP32S3ROM } from "./targets/esp32s3.js";
import { HardReset } from "./reset.js";
import { decodeBase64Data } from "./stubFlasher.js";

// Simplified loader
export class ESPLoader {
  constructor(port) {
    this.port = port;
    this.transport = new Transport(port);
    this.chip = new ESP32S3ROM(this.transport);
  }

  async initialize() {
    console.log("[loader] Initializing ESP32-S3...");
    await this.chip.sync();
    return this.chip;
  }

  async eraseFlash() {
    console.log("[loader] Erasing flash...");
    await this.chip.flash_begin();
  }

  async flashData(data, offset = 0x10000, compress = true) {
    console.log(`[loader] Flashing ${data.length} bytes at offset 0x${offset.toString(16)}`);
    await this.chip.flash_data(data, offset, compress);
  }

  async hardReset() {
    console.log("[loader] Hard reset...");
    const reset = new HardReset(this.transport);
    await reset.perform();
  }
}

// Optional helpers that your UI already uses
export { HardReset, decodeBase64Data, Transport };
