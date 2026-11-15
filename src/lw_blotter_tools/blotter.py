"""Blotter final format classes and utilities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from struct import pack
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _typeshed import SupportsWrite

_BLOTTER_HEADER = b"Logic World save"
_BLOTTER_FOOTER = b"redstone sux lol"
_BLOTTER_FORMAT_VERSION = b"\x07"
_BLOTTER_LW_GAME_VERSION = b"\x00\x00\x00\x00\x5c\x00\x00\x00\x04\x00\x00\x00\x12\x00\x00\x00"
_BLOTTER_PARTIAL_WORLD = b"\x02"
_BLOTTER_CORE_MOD_NAME = "MGH"
_BLOTTER_CORE_MOD_VERSION = b"\x00\x00\x00\x00\x5c\x00\x00\x00\x04\x00\x00\x00\xff\xff\xff\xff"
_BLOTTER_U8_MAX = 0xFF
_BLOTTER_U16_MAX = 0xFFFF
_BLOTTER_I32_MAX = 0x7FFFFFFF
_BLOTTER_I32_MIN = -0x80000000


class BlotterPegType(Enum):
    """Peg type possible values."""

    UNDEFINED = 0
    INPUT = 1
    OUTPUT = 2


@dataclass
class BlotterPegAddress:
    """Peg addresses, for use in wire definitions."""

    peg_type: BlotterPegType
    component_addr: int
    peg_index: int


@dataclass
class BlotterCircuitState:
    """Circuit state, for use in pegs and wires."""

    state: bool


@dataclass
class BlotterComponent:
    """A component placement in the save."""

    own_addr: int
    parent_addr: int
    cid: str
    position: tuple[int, int, int]
    rotation: tuple[float, float, float, float]
    inputs: list[BlotterCircuitState]
    outputs: list[BlotterCircuitState]
    custom_data: bytes


@dataclass
class BlotterWire:
    """A wire placement in the save."""

    first_addr: BlotterPegAddress
    second_addr: BlotterPegAddress
    circuit_state: BlotterCircuitState
    rotataion: float


class Blotter:
    """Container class for a subassembly."""

    def __init__(self) -> None:
        """Create an empty subassemly."""
        self.components: list[BlotterComponent] = []
        self.wires: list[BlotterWire] = []

    @staticmethod
    def _dump_bytes(f: SupportsWrite[bytes], data: bytes) -> None:
        f.write(data)

    @staticmethod
    def _dump_u8(f: SupportsWrite[bytes], i: int) -> None:
        if i > _BLOTTER_U8_MAX or i < 0:
            msg = "Uint8 must be in range [0, 2^8-1]"
            raise ValueError(msg)
        Blotter._dump_bytes(f, i.to_bytes(1, "little"))

    @staticmethod
    def _dump_u16(f: SupportsWrite[bytes], i: int) -> None:
        if i > _BLOTTER_U16_MAX or i < 0:
            msg = "Uint16 must be in range [0, 2^16-1]"
            raise ValueError(msg)
        Blotter._dump_bytes(f, i.to_bytes(2, "little"))

    @staticmethod
    def _dump_i32(f: SupportsWrite[bytes], i: int) -> None:
        if i > _BLOTTER_I32_MAX or i < _BLOTTER_I32_MIN:
            msg = "Int32 must be in range [-2^31, 2^32-1]"
            raise ValueError(msg)
        Blotter._dump_bytes(f, i.to_bytes(4, "little"))

    @staticmethod
    def _dump_f32(f: SupportsWrite[bytes], v: float) -> None:
        Blotter._dump_bytes(f, pack("f", v))

    @staticmethod
    def _dump_str(f: SupportsWrite[bytes], s: str) -> None:
        encoded = s.encode("utf-8")
        if len(encoded) > _BLOTTER_I32_MAX:
            msg = "Strings must be at most 2^31-1 bytes long"
            raise ValueError(msg)
        Blotter._dump_i32(f, len(encoded))
        Blotter._dump_bytes(f, encoded)

    @staticmethod
    def _dump_component_id_map(f: SupportsWrite[bytes], ci2id: dict[str, int]) -> None:
        if len(ci2id) > _BLOTTER_U16_MAX:
            msg = "Component ID maps can only have up to 2^16-1 IDs"
            raise ValueError(msg)

        Blotter._dump_i32(f, len(ci2id))
        for cid, idx in sorted(ci2id.items(), key=lambda p: p[1]):
            Blotter._dump_u16(f, idx)
            Blotter._dump_str(f, cid)

    @staticmethod
    def _dump_component(
        f: SupportsWrite[bytes], c: BlotterComponent, ci2id: dict[str, int], cs2id: dict[BlotterCircuitState, int]
    ) -> None:
        Blotter._dump_i32(f, c.own_addr)
        Blotter._dump_i32(f, c.parent_addr)
        Blotter._dump_u16(f, ci2id[c.cid])  # ID index into ID map
        Blotter._dump_i32(f, c.position[0])  # Pos X, in mm
        Blotter._dump_i32(f, c.position[1])  # Pos Y, in mm
        Blotter._dump_i32(f, c.position[2])  # Pos Z, in mm
        Blotter._dump_f32(f, c.rotation[0])  # Rot X, in mystery quaternion units
        Blotter._dump_f32(f, c.rotation[1])  # Rot Y, in mystery quaternion units
        Blotter._dump_f32(f, c.rotation[2])  # Rot Z, in mystery quaternion units
        Blotter._dump_f32(f, c.rotation[3])  # Rot W, in mystery quaternion units
        Blotter._dump_i32(f, len(c.inputs))
        for inp in c.inputs:
            Blotter._dump_i32(f, cs2id[inp])  # index into Circuit State map
        Blotter._dump_i32(f, len(c.outputs))
        for out in c.outputs:
            Blotter._dump_i32(f, cs2id[out])  # index into Circuit State map
        Blotter._dump_i32(f, len(c.custom_data))
        Blotter._dump_bytes(f, c.custom_data)

    @staticmethod
    def _dump_peg_address(f: SupportsWrite[bytes], pa: BlotterPegAddress) -> None:
        Blotter._dump_u8(f, pa.peg_type.value)
        Blotter._dump_i32(f, pa.component_addr)
        Blotter._dump_i32(f, pa.peg_index)

    @staticmethod
    def _dump_wire(f: SupportsWrite[bytes], w: BlotterWire, cs2id: dict[BlotterCircuitState, int]) -> None:
        Blotter._dump_peg_address(f, w.first_addr)
        Blotter._dump_peg_address(f, w.second_addr)
        Blotter._dump_i32(f, cs2id[w.circuit_state])
        Blotter._dump_f32(f, w.rotataion)

    def _compute_component_id_map(self) -> dict[str, int]:
        ci2id: dict[str, int] = {}

        for component in self.components:
            if component.cid in ci2id:
                continue
            ci2id[component.cid] = len(ci2id)

        return ci2id

    def _compute_circuit_state_map(self) -> dict[BlotterCircuitState, int]:
        cs2id: dict[BlotterCircuitState, int] = {}

        for wire in self.wires:
            if wire.circuit_state in cs2id:
                continue
            cs2id[wire.circuit_state] = len(cs2id)

        return cs2id

    def _gather_active_circuit_states(self, cs2id: dict[BlotterCircuitState, int]) -> list[int]:
        return [csid for cs, csid in cs2id.items() if cs]

    def dump(self, f: SupportsWrite[bytes]) -> None:
        """Dump the subassembly definition to a file-like object."""
        f.write(_BLOTTER_HEADER)

        # Verisoning
        f.write(_BLOTTER_FORMAT_VERSION)
        f.write(_BLOTTER_LW_GAME_VERSION)

        # World type
        # No support for full worlds, hardcoded partial world only
        f.write(_BLOTTER_PARTIAL_WORLD)

        # Data entry counts
        Blotter._dump_i32(f, len(self.components))
        Blotter._dump_i32(f, len(self.wires))

        # Mods
        # No support for mods yet, hardcoded core mod only
        Blotter._dump_i32(f, 1)
        Blotter._dump_str(f, _BLOTTER_CORE_MOD_NAME)
        f.write(_BLOTTER_CORE_MOD_VERSION)

        # Content pre-calculated values
        ci2id = self._compute_component_id_map()
        cs2id = self._compute_circuit_state_map()
        active_states = self._gather_active_circuit_states(cs2id)

        # Component ID map
        Blotter._dump_component_id_map(f, ci2id)

        # Component data
        for component in self.components:
            Blotter._dump_component(f, component, ci2id, cs2id)

        # Wire data
        for wire in self.wires:
            Blotter._dump_wire(f, wire, cs2id)

        # Circuit states
        Blotter._dump_i32(f, len(active_states))
        for state in active_states:
            Blotter._dump_i32(f, state)

        f.write(_BLOTTER_FOOTER)
