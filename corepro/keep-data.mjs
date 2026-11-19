const slots = [0x10000, 0x310000];
const sector = 4096;
const metadata = 0xe000;
const tableAddress = 0x8000;
const readPacketSize = 512;

export async function resetDevice(transport) {
  await transport.setDTR(false);
  await transport.setRTS(true);
  await new Promise(resolve => setTimeout(resolve, 200));
  await transport.setRTS(false);
  await new Promise(resolve => setTimeout(resolve, 200));
}

async function readFlash(loader, address, size) {
  if (!loader.IS_STUB) throw new Error('USB flash reader is unavailable');
  const request = new Uint8Array(16);
  const fields = new DataView(request.buffer);
  fields.setUint32(0, address, true);
  fields.setUint32(4, size, true);
  fields.setUint32(8, readPacketSize, true);
  fields.setUint32(12, 1, true); // Wait for each acknowledgement before sending more.
  const result = await loader.checkCommand('read flash', loader.ESP_READ_FLASH, request);
  if (result !== 0) throw new Error('USB flash read refused');

  const bytes = new Uint8Array(size);
  const acknowledgement = new DataView(new ArrayBuffer(4));
  for (let offset = 0; offset < size;) {
    const packet = await loader.transport.read(loader.FLASH_READ_TIMEOUT);
    if (packet.length !== Math.min(readPacketSize, size - offset)) {
      throw new Error('Incomplete USB flash packet');
    }
    bytes.set(packet, offset);
    offset += packet.length;
    acknowledgement.setUint32(0, offset, true);
    await loader.transport.write(new Uint8Array(acknowledgement.buffer));
  }
  // Consume the stub's final MD5 frame before sending any other command.
  const digest = await loader.transport.read(loader.FLASH_READ_TIMEOUT);
  if (digest.length !== 16) throw new Error('Missing USB flash digest');
  return bytes;
}

export async function sha256(bytes) {
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('');
}

function sequenceCrc(bytes) {
  // ESP-IDF bootloader uses esp_rom_crc32_le(UINT32_MAX, &ota_seq, 4).
  let crc = 0;
  for (const byte of bytes.subarray(0, 4)) {
    crc ^= byte;
    for (let i = 0; i < 8; i++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
  }
  return (~crc) >>> 0;
}

export function planUpdate(bytes) {
  if (bytes.length !== 2 * sector) throw new Error('Incomplete boot metadata');
  const records = [];
  for (let i = 0; i < 2; i++) {
    const entry = bytes.subarray(i * sector, i * sector + 32);
    if (entry.every(byte => byte === 255)) continue;
    const view = new DataView(entry.buffer, entry.byteOffset, entry.byteLength);
    const seq = view.getUint32(0, true);
    const state = view.getUint32(24, true);
    // Espressif's boot_app0 seed uses a zero sequence with an erased tail.
    if (seq === 0 && entry.subarray(4).every(byte => byte === 255)) continue;
    if (!seq || seq === 0xffffffff || sequenceCrc(entry) !== view.getUint32(28, true) ||
        ![0, 1, 2, 3, 4, 0xffffffff].includes(state)) throw new Error('Unrecognized boot metadata');
    if (state !== 3 && state !== 4) records.push({i, seq, state});
  }
  records.sort((a, b) => b.seq - a.seq);
  const active = records[0];
  if ((!active && bytes.some(byte => byte !== 255)) ||
      (active && (![2, 0xffffffff].includes(active.state) || active.seq >= 0xfffffffe || records[1]?.seq === active.seq))) {
    throw new Error('The running firmware has no confirmed boot slot');
  }
  const activeSlot = active ? (active.seq - 1) % 2 : 0;
  const selection = new Uint8Array(sector).fill(255);
  const view = new DataView(selection.buffer);
  view.setUint32(0, active ? active.seq + 1 : 2, true);
  view.setUint32(24, 0, true); // NEW: let the firmware's first-boot checks run.
  view.setUint32(28, sequenceCrc(selection), true);
  return {
    activeAddress: slots[activeSlot],
    targetAddress: slots[1 - activeSlot],
    selectionAddress: metadata + (active ? 1 - active.i : 0) * sector,
    selection,
  };
}

export async function withDeadline(action, label, timeoutMs = 15000) {
  let timer;
  try {
    return await Promise.race([
      Promise.resolve().then(action),
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error(label + ' timed out')), timeoutMs);
      }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}

export async function updateFirmware(loader, release, application, status) {
  const check = (label, action) => {
    status(label + '…');
    return withDeadline(action, label);
  };
  if (application.length !== release.size || application.length > 0x300000 ||
      await sha256(application) !== release.sha256) throw new Error('Firmware integrity check failed');
  if (await sha256(await check('Reading flash layout', () => readFlash(loader, tableAddress, sector))) !== release.partitionSha256) {
    throw new Error('This device uses a different flash layout');
  }
  const plan = planUpdate(await check('Reading boot slot', () => readFlash(loader, metadata, 2 * sector)));
  async function write(address, data) {
    await loader.writeFlash({
      fileArray: [{address, data}], flashMode: 'keep', flashFreq: 'keep', flashSize: 'keep',
      eraseAll: false, compress: true,
      reportProgress: (_, done, total) => status(`Writing firmware · ${Math.floor(100 * done / total)}%`),
    });
  }
  status('Writing the inactive firmware slot…');
  await write(plan.targetAddress, application);
  status('Verifying the written firmware…');
  if ((await loader.flashMd5sum(plan.targetAddress, application.length)).toLowerCase() !== release.md5) {
    throw new Error('Firmware write verification failed');
  }
  // Leave the previously selected sector and its firmware intact.
  status('Selecting the verified firmware for next boot…');
  await write(plan.selectionAddress, plan.selection);
  const selected = await check('Reading back boot selection', () => readFlash(loader, plan.selectionAddress, sector));
  if (await sha256(selected) !== await sha256(plan.selection)) throw new Error('Boot selection verification failed');
}
