"""Version-checked DOS intro evidence; contains no executable or artwork."""
import hashlib
import struct

EXE_SHA256 = '1f6d7bd92a8336818b65cc2157b5929dc353613258bfe8de6c83d23bb07a10ef'
CREDIT_STEPS = (328,328,344,240,240,240,240,320,390,376,390,360,390,290,130)
STORY_PHASES = (3,3,4,4)
STORY_RETRACES = 250


def inspect(data):
    if hashlib.sha256(data).hexdigest() != EXE_SHA256:
        raise ValueError('intro evidence requires the audited DOS executable')
    checks = {
        0x11a37: 'bb5a45bf3c4553578b0f81c1a000e8a600',
        0x11aee: '8b1e7dafbad403b00c8ae7effec08ae3ef031e7faf519a580cb91159',
        0x1fa34: 'bf2819b800a08ec08ed8b91806f3a4',
    }
    for offset, code in checks.items():
        if data[offset:offset+len(bytes.fromhex(code))] != bytes.fromhex(code):
            raise ValueError(f'intro instruction mismatch at {offset:05x}')
    if struct.unpack_from('<2H',data,0x22f00+0xaf7d) != (1600,40):
        raise ValueError('16-colour video stride mismatch')
    distances = tuple((x+160)&65535 for x in struct.unpack_from('<15h',data,0x22f00+0x455a))
    if distances != CREDIT_STEPS:
        raise ValueError('credit distance table mismatch')
    return dict(exe_sha256=EXE_SHA256,credit_steps=list(distances),
                viewport_height=160,logo_height=40,source_height=600,
                initial_display_address=1600,bytes_per_scanline=40,
                nominal_retraces_per_second=70,
                story_retraces=STORY_RETRACES,story_phases=list(STORY_PHASES),
                story_text_source_y=[200,239,278],story_text_destination_y=161,
                story_text_height=39,code={hex(k):v for k,v in checks.items()})
