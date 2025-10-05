/**
 * Represents a chip ROM with basic registers field and abstract functions.
 */
export class ROM {
    constructor() {
        this.FLASH_SIZES = {
            "1MB": 0x00,
            "2MB": 0x10,
            "4MB": 0x20,
            "8MB": 0x30,
            "16MB": 0x40,
            "32MB": 0x50,
            "64MB": 0x60,
            "128MB": 0x70,
        };
        this.FLASH_FREQUENCY = {
            "80m": 0xf,
            "40m": 0x0,
            "26m": 0x1,
            "20m": 0x2,
        };
    }
    /**
     * Get the chip erase size.
     * @param {number} offset - Offset to start erase.
     * @param {number} size - Size to erase.
     * @returns {number} The erase size of the chip as number.
     */
    getEraseSize(offset, size) {
        return size;
    }
}
