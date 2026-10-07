"""A small, dependency-free reader for SPSS system files (.sav and .zsav).

TIMSS and PISA distribute their data as SPSS files, and the usual Python reader
(``pyreadstat``) needs a compiled extension. This reader covers what assessment files use:
numeric and string variables, bytecode (``.sav``) and zlib (``.zsav``) compression, long
variable names, value labels and user-missing declarations. User-missing codes are returned
as their raw values (for example TIMSS's 6 = not reached, 9 = omitted), so that scoring rules
can treat them deliberately; system-missing becomes NaN.

    from algebradx.sav import read_sav
    df, meta = read_sav("bsausam7.sav", usecols=["IDSTUD", "TOTWGT", "ME72188"])

Format reference: the PSPP documentation of the SPSS system-file format
(https://www.gnu.org/software/pspp/pspp-dev/html_node/System-File-Format.html).
"""
from __future__ import annotations

import io
import struct
import zlib
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

SYSMIS = -np.finfo(np.float64).max


@dataclass
class SavMeta:
    n_cases: int
    columns: list
    widths: dict                       # 0 = numeric, else string width
    labels: dict = field(default_factory=dict)          # variable labels
    value_labels: dict = field(default_factory=dict)    # var -> {value: label}
    missing: dict = field(default_factory=dict)         # var -> declared user-missing spec
    encoding: str = "latin-1"
    compression: int = 0


class _R:
    def __init__(self, f, endian):
        self.f, self.e = f, endian

    def i32(self):
        return struct.unpack(self.e + "i", self.f.read(4))[0]

    def f64(self):
        return struct.unpack(self.e + "d", self.f.read(8))[0]

    def raw(self, n):
        b = self.f.read(n)
        if len(b) != n:
            raise EOFError("unexpected end of SPSS file")
        return b


def _read_dictionary(f):
    head = f.read(176)
    if head[:4] not in (b"$FL2", b"$FL3"):
        raise ValueError("not an SPSS system file")
    layout_le = struct.unpack("<i", head[64:68])[0]
    endian = "<" if layout_le in (2, 3) else ">"
    case_size, compression, _w, n_cases = struct.unpack(endian + "iiii", head[68:84])
    bias = struct.unpack(endian + "d", head[84:92])[0]
    r = _R(f, endian)
    slots = []                      # one entry per 8-byte slot: (name or None, width)
    short_names, widths, var_labels, missing = [], {}, {}, {}
    vl_pending, value_labels = None, {}
    long_names, very_long, encoding = {}, {}, None
    while True:
        rt = r.i32()
        if rt == 2:
            vtype, has_label, n_miss = r.i32(), r.i32(), r.i32()
            r.raw(8)                                  # print / write formats
            name = r.raw(8).decode("latin-1").rstrip()
            if has_label:
                n = r.i32()
                lab = r.raw((n + 3) // 4 * 4)[:n]
            else:
                lab = None
            miss = [r.f64() for _ in range(abs(n_miss))] if n_miss else []
            if vtype == -1:
                slots.append((None, -1))
                continue
            slots.append((name, vtype))
            short_names.append(name)
            widths[name] = vtype
            if lab is not None:
                var_labels[name] = lab
            if miss:
                missing[name] = {"range" if n_miss < 0 else "values": miss}
        elif rt == 3:
            n = r.i32()
            labs = {}
            for _ in range(n):
                val = r.raw(8)
                ln = r.raw(1)[0]
                text = r.raw((ln + 8) // 8 * 8 - 1)[:ln]
                labs[val] = text
            vl_pending = labs
        elif rt == 4:
            n = r.i32()
            idx = [r.i32() for _ in range(n)]
            for i in idx:
                name = slots[i - 1][0]
                if name is None:
                    continue
                conv = {}
                for k, v in (vl_pending or {}).items():
                    key = struct.unpack(endian + "d", k)[0] if widths[name] == 0 else k
                    conv[key] = v
                value_labels[name] = conv
            vl_pending = None
        elif rt == 6:
            r.raw(80 * r.i32())
        elif rt == 7:
            sub, size, count = r.i32(), r.i32(), r.i32()
            data = r.raw(size * count)
            if sub == 13:
                for pair in data.split(b"\t"):
                    if b"=" in pair:
                        a, b = pair.split(b"=", 1)
                        long_names[a.decode("latin-1")] = b
            elif sub == 14:
                for pair in data.split(b"\x00\t"):
                    pair = pair.strip(b"\x00")
                    if b"=" in pair:
                        a, b = pair.split(b"=", 1)
                        very_long[a.decode("latin-1")] = int(b)
            elif sub == 20:
                encoding = data.decode("ascii", "ignore").strip() or None
        elif rt == 999:
            r.i32()
            break
        else:
            raise ValueError(f"unknown SPSS record type {rt}")
    enc = {"UTF-8": "utf-8", "WINDOWS-1252": "cp1252"}.get((encoding or "").upper(), encoding or "latin-1")
    try:
        "".encode(enc)
    except LookupError:
        enc = "latin-1"
    names = {s: long_names.get(s, s.encode()).decode(enc) for s in short_names}
    meta = SavMeta(
        n_cases=n_cases, columns=[names[s] for s in short_names],
        widths={names[s]: w for s, w in widths.items()},
        labels={names[s]: v.decode(enc, "replace") for s, v in var_labels.items()},
        value_labels={names[s]: {k: v.decode(enc, "replace") for k, v in d.items()}
                      for s, d in value_labels.items()},
        missing={names[s]: v for s, v in missing.items()}, encoding=enc, compression=compression)
    return meta, slots, names, endian, bias, case_size, compression


def _decompress_bytecode(stream, bias, endian, nslots):
    """Yield the data as a flat sequence of 8-byte slots (bytes objects)."""
    out = io.BytesIO()
    spaces = b" " * 8
    sysmis = struct.pack(endian + "d", SYSMIS)
    while True:
        cmd = stream.read(8)
        if len(cmd) < 8:
            break
        for c in cmd:
            if c == 0:
                continue
            if c == 252:
                return out.getvalue()
            if c == 253:
                out.write(stream.read(8))
            elif c == 254:
                out.write(spaces)
            elif c == 255:
                out.write(sysmis)
            else:
                out.write(struct.pack(endian + "d", c - bias))
    return out.getvalue()


def _zsav_stream(f, endian):
    zheader = f.read(24)
    zh_ofs, zt_ofs, zt_len = struct.unpack(endian + "qqq", zheader)
    f.seek(zt_ofs)
    _bias, _zero, _block, n_blocks = struct.unpack(endian + "qqii", f.read(24))
    parts = []
    for _ in range(n_blocks):
        _uofs, cofs, _usize, csize = struct.unpack(endian + "qqii", f.read(24))
        pos = f.tell()
        f.seek(cofs)
        parts.append(zlib.decompress(f.read(csize)))
        f.seek(pos)
    return io.BytesIO(b"".join(parts))


def read_sav(path, usecols=None, row_filter=None):
    """Read an SPSS system file into a DataFrame.

    usecols : list of column names to keep (others are skipped after decoding).
    row_filter : optional (column, value) pair, e.g. ("CNT", "USA"), applied while reading.
    Returns (DataFrame, SavMeta).
    """
    with open(path, "rb") as f:
        meta, slots, names, endian, bias, case_size, compression = _read_dictionary(f)
        if compression == 0:
            raw = f.read()
        elif compression == 1:
            raw = _decompress_bytecode(f, bias, endian, len(slots))
        elif compression == 2:
            raw = _decompress_bytecode(_zsav_stream(f, endian), bias, endian, len(slots))
        else:
            raise ValueError(f"unsupported compression {compression}")
    nslots = len(slots)
    ncase = len(raw) // (8 * nslots)
    buf = np.frombuffer(raw[: ncase * nslots * 8], dtype=np.uint8).reshape(ncase, nslots * 8)
    want = set(usecols) if usecols is not None else None
    if row_filter is not None and want is not None:
        want = want | {row_filter[0]}
    cols = {}
    i = 0
    while i < nslots:
        short, width = slots[i]
        name = names[short]
        nsl = 1 if width == 0 else (width + 7) // 8
        # very long strings span several segments; they are rare in assessment files
        if want is None or name in want:
            block = buf[:, i * 8:(i + nsl) * 8]
            if width == 0:
                v = block.copy().view(endian + "f8").ravel().astype(np.float64)
                v[v == SYSMIS] = np.nan
                cols[name] = v
            else:
                cols[name] = [bytes(row[:width]).decode(meta.encoding, "replace").rstrip()
                              for row in block]
        i += nsl
    df = pd.DataFrame(cols)
    if row_filter is not None:
        df = df[df[row_filter[0]] == row_filter[1]].reset_index(drop=True)
    if usecols is not None:
        df = df[[c for c in usecols if c in df.columns]]
    return df, meta
