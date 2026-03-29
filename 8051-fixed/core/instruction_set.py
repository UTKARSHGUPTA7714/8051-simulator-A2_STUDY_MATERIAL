from core.util import decompose_byte, twos_complement


class Instructions:
    def __init__(self, op) -> None:
        self.op = op
        self._jump_flag = False
        self._jump_instructions = op._jump_instructions
        self._base = 16
        self.flags = self.op.super_memory.PSW
        pass

    def _is_jump_opcode(self, opcode) -> bool:
        opcode = opcode.upper()
        if opcode not in self._jump_instructions:
            return False
        return True

    def _next_addr(self, addr) -> str:
        return format(int(str(addr), 16) + 1, "#06x")

    def _check_carry(self, data_1, data_2, og2, add=True, _AC=True, _CY=True) -> None:
        decomposed_data_1 = decompose_byte(data_1, nibble=True)
        decomposed_data_2 = decompose_byte(data_2, nibble=True)
        carry_data, aux_data = list(zip(decomposed_data_1, decomposed_data_2))

        if _AC:
            self.flags.AC = False
            if (int(aux_data[0], 16) + int(aux_data[1], 16)) >= 16:
                print("AUX FLAG")
                self.flags.AC = True

        if not _CY:
            return

        if not add:
            self.flags.CY = False
            if int(str(data_1), 16) < int(str(og2), 16):
                print("CARRY FLAG-")
                self.flags.CY = True
        return

    def _check_parity(self, data_bin: str) -> None:
        self.flags.P = False
        _count_1s = data_bin.count("1")
        if not _count_1s % 2:
            self.flags.P = True
            print("PARITY")
        return

    def _check_overflow(self, data_bin: str) -> None:
        self.flags.OV = False
        if int(data_bin[0]):
            self.flags.OV = True
            print("SIGN")
        return

    def _check_flags(self, data_bin, _P=True, _OV=True) -> bool:
        if _P:
            self._check_parity(data_bin)
        if _OV:
            self._check_overflow(data_bin)
        return True

    def _check_flags_and_compute(self, data_1, data_2, add=True, _AC=True, _CY=True, _P=True, _OV=True):
        og2 = data_2
        if not add:
            data_2 = twos_complement(str(data_2))

        result = int(str(data_1), 16) + int(str(data_2), 16)
        if result > 255:
            if _CY:
                self.flags.CY = True
                print("CARRY FLAG+")
            result -= 256
        result_hex = format(result, "#04x")
        data_bin = format(result, "08b")

        self._check_carry(data_1, data_2, og2, add=add, _AC=_AC, _CY=_CY)
        self._check_flags(data_bin, _P=_P, _OV=_OV)
        return result_hex

    def _resolve_addressing_mode(self, addr, data=None) -> tuple:
        if str(addr)[0] == "@":  # Register indirect
            addr = self.op.memory_read(str(addr)[1:])

        if data is not None:
            data = str(data)
            if data[0] == "@":  # Register indirect
                data = self.op.memory_read(data[1:])
            elif data[0] == "#":  # Immediate addressing
                data = data[1:]
            else:
                data = self.op.memory_read(data)
        return addr, data

    def _int(self, val) -> int:
        """Safely convert Byte / str / int to Python int."""
        return int(str(val), 16)

    # ── NOP ─────────────────────────────────────────────────────────────────

    def nop(self, *args, **kwargs) -> bool:
        """No operation."""
        return True

    # ── Data Transfer ────────────────────────────────────────────────────────

    def mov(self, addr, data) -> bool:
        addr, data = self._resolve_addressing_mode(addr, data)
        return self.op.memory_write(addr, data)

    def movc(self, addr, data) -> bool:
        """MOVC A, @A+DPTR  or  MOVC A, @A+PC"""
        a_val = self._int(self.op.memory_read("A"))
        if "DPTR" in str(data).upper():
            base = self._int(self.op.super_memory.DPTR.read())
        else:
            base = self._int(str(self.op.super_memory.PC))
        effective = (a_val + base) & 0xFFFF
        try:
            result = self.op.memory_read(format(effective, "#06x"), RAM=False)
        except Exception:
            result = "0x00"
        return self.op.memory_write("A", result)

    def movx(self, addr, data) -> bool:
        """MOVX — external data memory (simplified: mapped to internal RAM)."""
        addr, data = self._resolve_addressing_mode(addr, data)
        return self.op.memory_write(addr, data)

    def push(self, addr: str) -> bool:
        """Push direct byte onto stack."""
        data = self.op.memory_read(addr)
        return self.op.super_memory.SP.write(data)

    def pop(self, addr: str) -> bool:
        """Pop stack top into direct address."""
        data = self.op.super_memory.SP.read()
        return self.op.memory_write(addr, data)

    def xch(self, addr_1, addr_2) -> bool:
        """XCH A, <src> — exchange A with operand."""
        addr_1, _ = self._resolve_addressing_mode(addr_1)
        addr_2, _ = self._resolve_addressing_mode(addr_2)
        d1 = self.op.memory_read(addr_1)
        d2 = self.op.memory_read(addr_2)
        self.op.memory_write(str(addr_1), d2)
        self.op.memory_write(str(addr_2), d1)
        return True

    def xchd(self, addr_1, addr_2) -> bool:
        """XCHD A, @Ri — exchange lower nibble of A with lower nibble of [Ri]."""
        addr_1, _ = self._resolve_addressing_mode(addr_1)
        if str(addr_2).startswith("@"):
            addr_2 = str(self.op.memory_read(str(addr_2)[1:]))
        else:
            addr_2, _ = self._resolve_addressing_mode(addr_2)
        d1 = self._int(self.op.memory_read(str(addr_1)))
        d2 = self._int(self.op.memory_read(str(addr_2)))
        self.op.memory_write(str(addr_1), format((d1 & 0xF0) | (d2 & 0x0F), "#04x"))
        self.op.memory_write(str(addr_2), format((d2 & 0xF0) | (d1 & 0x0F), "#04x"))
        return True

    # ── Arithmetic ───────────────────────────────────────────────────────────

    def add(self, addr, data) -> bool:
        addr, data_1 = self._resolve_addressing_mode(addr, data)
        data_2 = self.op.memory_read(addr)
        return self.op.memory_write(addr, self._check_flags_and_compute(data_1, data_2))

    def addc(self, addr, data) -> bool:
        """ADD with carry."""
        addr, data_1 = self._resolve_addressing_mode(addr, data)
        data_2 = self.op.memory_read(addr)
        carry = 1 if self.flags.CY else 0
        data_1 = format((self._int(data_1) + carry) & 0xFF, "#04x")
        return self.op.memory_write(addr, self._check_flags_and_compute(data_1, data_2))

    def subb(self, addr, data) -> bool:
        addr, data_2 = self._resolve_addressing_mode(addr, data)
        data_1 = self.op.memory_read(addr)
        if self.flags.CY:
            self.flags.CY = False
            data_2 = format(self._int(data_2) + 1, "#04x")
        return self.op.memory_write(addr, self._check_flags_and_compute(data_1, data_2, add=False))

    def mul(self, *args) -> bool:
        """MUL AB — result in B:A (B=high, A=low)."""
        a = self._int(self.op.memory_read("A"))
        b = self._int(self.op.memory_read("B"))
        result = a * b
        self.flags.CY = False
        self.flags.OV = result > 255
        self.op.memory_write("A", format(result & 0xFF, "#04x"))
        self.op.memory_write("B", format((result >> 8) & 0xFF, "#04x"))
        return True

    def div(self, *args) -> bool:
        """DIV AB — quotient in A, remainder in B."""
        a = self._int(self.op.memory_read("A"))
        b = self._int(self.op.memory_read("B"))
        if b == 0:
            self.flags.OV = True
            self.flags.CY = False
            return True
        self.flags.CY = False
        self.flags.OV = False
        self.op.memory_write("A", format(a // b, "#04x"))
        self.op.memory_write("B", format(a % b, "#04x"))
        return True

    def inc(self, addr) -> bool:
        addr, _ = self._resolve_addressing_mode(addr)
        if str(addr).upper() == "DPTR":
            new_val = (self._int(self.op.super_memory.DPTR.read()) + 1) & 0xFFFF
            self.op.super_memory.DPTR.write(format(new_val, "#06x"))
            return True
        data = self.op.memory_read(addr)
        return self.op.memory_write(addr, format((self._int(data) + 1) & 0xFF, "#04x"))

    def dec(self, addr) -> bool:
        addr, _ = self._resolve_addressing_mode(addr)
        print(f"addr: {addr}")
        data = self.op.memory_read(addr)
        return self.op.memory_write(
            addr,
            self._check_flags_and_compute(data, "0x01", add=False, _CY=False, _AC=False, _P=False, _OV=False),
        )

    def da(self, addr: str) -> bool:
        """DA A — decimal adjust after BCD addition."""
        addr, _ = self._resolve_addressing_mode(addr)
        data = self._int(self.op.memory_read(addr))
        if (data & 0x0F) > 9 or self.flags.AC:
            data += 6
        if (data >> 4) > 9 or self.flags.CY:
            data += 0x60
            self.flags.CY = True
        data &= 0xFF
        return self.op.memory_write(addr, format(data, "#04x"))

    # ── Logic ────────────────────────────────────────────────────────────────

    def anl(self, addr_1, addr_2) -> bool:
        """ANL — bitwise AND; all addressing modes supported."""
        addr_1, data_2 = self._resolve_addressing_mode(addr_1, addr_2)
        result = self._int(self.op.memory_read(addr_1)) & self._int(data_2)
        self.op.memory_write(addr_1, format(result, "#04x"))
        return self._check_flags(format(result, "08b"))

    def orl(self, addr_1, addr_2) -> bool:
        """ORL — bitwise OR; all addressing modes supported."""
        addr_1, data_2 = self._resolve_addressing_mode(addr_1, addr_2)
        result = self._int(self.op.memory_read(addr_1)) | self._int(data_2)
        self.op.memory_write(addr_1, format(result, "#04x"))
        return self._check_flags(format(result, "08b"))

    def xrl(self, addr_1, addr_2) -> bool:
        """XRL — bitwise XOR; all addressing modes supported."""
        addr_1, data_2 = self._resolve_addressing_mode(addr_1, addr_2)
        result = self._int(self.op.memory_read(addr_1)) ^ self._int(data_2)
        self.op.memory_write(addr_1, format(result, "#04x"))
        return self._check_flags(format(result, "08b"))

    def clr(self, bit: str) -> bool:
        """CLR A — zero the accumulator.  CLR C / CLR bit — clear flag/bit."""
        if bit.upper() == "A":
            return self.op.memory_write("A", "0x00")
        return self.op.bit_write(bit, False)

    def setb(self, bit: str) -> bool:
        """SETB C / SETB bit — set carry or bit address."""
        return self.op.bit_write(bit, True)

    def cpl(self, bit: str) -> bool:
        """CPL A — complement accumulator.  CPL C / CPL bit — complement bit."""
        if bit.upper() == "A":
            return self.op.memory_write("A", format(~self._int(self.op.memory_read("A")) & 0xFF, "#04x"))
        _data = self.op.bit_read(bit)
        return self.op.bit_write(bit, not _data)

    # ── Rotate / Shift ───────────────────────────────────────────────────────

    def rl(self, addr) -> bool:
        """RL A — rotate left without carry."""
        addr, _ = self._resolve_addressing_mode(addr)
        data = self._int(self.op.memory_read(addr))
        return self.op.memory_write("A", format(((data << 1) | (data >> 7)) & 0xFF, "#04x"))

    def rr(self, addr) -> bool:
        """RR A — rotate right without carry."""
        addr, _ = self._resolve_addressing_mode(addr)
        data = self._int(self.op.memory_read(addr))
        return self.op.memory_write("A", format(((data >> 1) | ((data & 1) << 7)) & 0xFF, "#04x"))

    def rlc(self, addr) -> bool:
        """RLC A — rotate left through carry."""
        addr, _ = self._resolve_addressing_mode(addr)
        data = self._int(self.op.memory_read(addr))
        old_cy = 1 if self.flags.CY else 0
        self.flags.CY = bool((data >> 7) & 1)
        return self.op.memory_write("A", format(((data << 1) | old_cy) & 0xFF, "#04x"))

    def rrc(self, addr) -> bool:
        """RRC A — rotate right through carry."""
        addr, _ = self._resolve_addressing_mode(addr)
        data = self._int(self.op.memory_read(addr))
        old_cy = 1 if self.flags.CY else 0
        self.flags.CY = bool(data & 1)
        return self.op.memory_write("A", format(((data >> 1) | (old_cy << 7)) & 0xFF, "#04x"))

    def swap(self, addr) -> bool:
        """SWAP A — exchange upper and lower nibbles."""
        addr, _ = self._resolve_addressing_mode(addr)
        data = self._int(self.op.memory_read(addr))
        return self.op.memory_write(addr, format(((data & 0x0F) << 4) | ((data & 0xF0) >> 4), "#04x"))

    # ── Assembler Directive ──────────────────────────────────────────────────

    def org(self, addr) -> bool:
        """ORG — set origin of program counter."""
        return self.op.super_memory.PC(addr)

    # ── Subroutine / Return ──────────────────────────────────────────────────

    def ret(self, *args, **kwargs) -> bool:
        """RET — return from subroutine (pop PC from stack)."""
        high = self.op.super_memory.SP.read()
        low = self.op.super_memory.SP.read()
        self.op.super_memory.PC(format((self._int(high) << 8) | self._int(low), "#06x"))
        return True

    def reti(self, *args, **kwargs) -> bool:
        """RETI — return from interrupt."""
        return self.ret(*args, **kwargs)

    def acall(self, label, *args, **kwargs) -> bool:
        """ACALL — push PC then jump to label."""
        bounce_to_label = kwargs.get("bounce_to_label")
        pc_val = self._int(str(self.op.super_memory.PC))
        self.op.super_memory.SP.write(format(pc_val & 0xFF, "#04x"))
        self.op.super_memory.SP.write(format((pc_val >> 8) & 0xFF, "#04x"))
        if bounce_to_label:
            return bounce_to_label(label)
        return True

    def lcall(self, label, *args, **kwargs) -> bool:
        """LCALL — push PC then jump to label (same as ACALL in simulator)."""
        return self.acall(label, *args, **kwargs)

    # ── Unconditional Jumps ──────────────────────────────────────────────────

    def sjmp(self, label, *args, **kwargs) -> bool:
        """SJMP — short unconditional jump."""
        bounce_to_label = kwargs.get("bounce_to_label")
        if bounce_to_label:
            return bounce_to_label(label)
        return True

    def ajmp(self, label, *args, **kwargs) -> bool:
        """AJMP — absolute unconditional jump."""
        return self.sjmp(label, *args, **kwargs)

    def ljmp(self, label, *args, **kwargs) -> bool:
        """LJMP — long unconditional jump."""
        return self.sjmp(label, *args, **kwargs)

    def jmp(self, label, *args, **kwargs) -> bool:
        """JMP — generic jump (JMP @A+DPTR handled as no-op for computed case)."""
        lstr = str(label).upper()
        if "DPTR" in lstr or "@" in lstr:
            return True  # computed jump — can't trace label; treated as NOP
        return self.sjmp(label, *args, **kwargs)

    # ── Conditional Jumps ────────────────────────────────────────────────────

    def jz(self, label, *args, **kwargs) -> bool:
        """JZ — jump if accumulator is zero."""
        bounce_to_label = kwargs.get("bounce_to_label")
        if self._int(self.op.memory_read("A")) == 0:
            return bounce_to_label(label)
        return True

    def jnz(self, label, *args, **kwargs) -> bool:
        """JNZ — jump if accumulator is not zero."""
        bounce_to_label = kwargs.get("bounce_to_label")
        if self._int(self.op.memory_read("A")) != 0:
            return bounce_to_label(label)
        return True

    def jc(self, label, *args, **kwargs) -> bool:
        """JC — jump if carry."""
        bounce_to_label = kwargs.get("bounce_to_label")
        if self.op.flags.CY:
            return bounce_to_label(label)
        return True

    def jnc(self, label, *args, **kwargs) -> bool:
        """JNC — jump if no carry."""
        bounce_to_label = kwargs.get("bounce_to_label")
        if not self.op.flags.CY:
            return bounce_to_label(label)
        return True

    def jb(self, addr, label, *args, **kwargs) -> bool:
        """JB bit, label — jump if bit is set."""
        bounce_to_label = kwargs.get("bounce_to_label")
        if self.op.bit_read(addr):
            return bounce_to_label(label)
        return True

    def jnb(self, addr, label, *args, **kwargs) -> bool:
        """JNB bit, label — jump if bit is clear."""
        bounce_to_label = kwargs.get("bounce_to_label")
        if not self.op.bit_read(addr):
            return bounce_to_label(label)
        return True

    def jbc(self, addr, label, *args, **kwargs) -> bool:
        """JBC bit, label — jump if bit set, then clear bit."""
        bounce_to_label = kwargs.get("bounce_to_label")
        if self.op.bit_read(addr):
            self.op.bit_write(addr, False)
            return bounce_to_label(label)
        return True

    def djnz(self, addr, label, *args, **kwargs) -> bool:
        """DJNZ reg/direct, label — decrement and jump if not zero."""
        bounce_to_label = kwargs.get("bounce_to_label")
        if label == "offset":
            label = addr
            addr = "A"
        result = (self._int(self.op.memory_read(addr)) - 1) & 0xFF
        self.op.memory_write(addr, format(result, "#04x"))
        if result != 0:
            return bounce_to_label(label)
        return True

    def cjne(self, addr, addr2, label, *args, **kwargs) -> bool:
        """CJNE — compare and jump if not equal."""
        bounce_to_label = kwargs.get("bounce_to_label")
        data_1 = self._int(self.op.memory_read(addr))
        if str(addr2).startswith("#"):
            data_2 = int(str(addr2)[1:], 16)
        else:
            _a2, _ = self._resolve_addressing_mode(addr2)
            data_2 = self._int(self.op.memory_read(str(_a2)))
        if data_1 != data_2:
            self.flags.CY = data_1 < data_2
            return bounce_to_label(label)
        self.flags.CY = False
        return True

    pass
