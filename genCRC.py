import binascii

# 入力：CRC未付与の16進数文字列（スペース区切り）
hex_input = '''
03 05 00 FF 0C 02 04 01 01 43 48 30 20 4A 41 50 41 4E 2D 57 45 53 54 4C 41 42 2D 54 45 53 54 45 4E 56 20 50 57 4D
'''
#03 05 00 FF 0C 02 04 01 01 43 48 30 20 4A 41 50 41 4E 2D 57 45 53 54 4C 41 42 2D 54 45 53 54 45 4E 56 20 54 45 4D 50
#03 05 00 FF 0C 02 04 01 01 43 48 30 20 4A 41 50 41 4E 2D 57 45 53 54 4C 41 42 2D 54 45 53 54 45 4E 56 20 48 55 4D 49 44

# スペース・改行を除去してバイト列に変換
data_bytes = bytes.fromhex(hex_input.strip())

# CRC-16-CCITT 計算（poly=0x1021, init=0xFFFF, no inversion, no final XOR）
def compute_crc16_ccitt(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = (crc << 1) ^ 0x1021 if (crc & 0x8000) else crc << 1
            crc &= 0xFFFF
    return crc

# CRC計算
crc = compute_crc16_ccitt(data_bytes)

# CRCを末尾に追加
teds_with_crc = data_bytes + crc.to_bytes(2, 'big')

# 16進数文字列で表示（スペース区切り）
hex_output = ' '.join(f'{b:02X}' for b in teds_with_crc)
print(hex_output)
