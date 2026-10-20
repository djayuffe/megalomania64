#!/usr/bin/env python3
"""Focused v5 mutation checks. Run the normal test suite first.

Each mutant runs one regression test in an isolated copy. Assembly/import errors
are not accepted as kills: the selected test must fail an assertion.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CASES=[
 ('src/music.asm',' cmp #$c0\n bne mu_sustained',' cmp #$ff\n bne mu_sustained','test_music.py','test_percussion_has_a_decaying_envelope_instead_of_sustained_noise'),
 ('src/sample.asm',' lda sid_8580\n beq sm_muted',' lda #0\n beq sm_muted','test_intro.py','test_8580_detection_boosts_three_dc_sources_and_stop_removes_every_test_bit'),
 ('src/sample.asm',' ora #6\n sta $01',' ora #0\n sta $01','test_intro.py','test_nested_nmi_during_banked_read_acknowledges_the_real_cia'),
 ('src/loader.asm',' and #$f8\n sta $01',' and #$ff\n sta $01','test_av_fixes.py','test_complete_bank_loads_without_touching_sid_registers'),
 ('src/sample.asm',' lda fx_ready\n beq sm_no_wrap',' lda #0\n beq sm_no_wrap','test_av_fixes.py','test_a_full_clip_crosses_the_two_regions_and_finishes_at_its_exact_end'),
 ('src/sample.asm',' lda #$49\n sta $d412',' lda #$48\n sta $d412','test_intro.py','test_sid_voices_are_muted_while_a_sample_plays_and_restored_after'),
 ('tools/vic_bitmap.py','distance+=neutral[:,:,None]*chromatic[None,None,:]','distance+=0','test_av_fixes.py','test_grey_text_does_not_turn_brown'),
 ('src/sample.asm',' bne sm_neout                ; VIC DMA can stretch a digi NMI past the next timer edge',' nop\n nop','test_intro.py','test_nested_nmi_cannot_underflow_the_last_sample_counter'),
 ('src/intro.asm',' jsr $ffcc                    ; GETIN otherwise reads the selected disk channel!',' nop','test_streaming.py','test_keyboard_poll_does_not_consume_the_disk_channel'),
 ('src/loader.asm',' lda ld_eof\n bne ld_fail_read',' lda #0\n nop\n nop','test_streaming.py','test_last_byte_is_valid_and_next_read_fails'),
 ('src/sample.asm',' and #$fd\n sta $01',' and #$ff\n sta $01','test_streaming.py','test_voice_wraps_from_7fff_to_e000_and_restores_cpu_port'),
 ('src/level.asm',' lda #$30\n sta $d015',' lda #0\n sta $d015','test_streaming.py','test_island_card_restores_vic_registers_and_preserves_speech'),
 ('src/music.asm',' cmp #6\n bcc mu_frame',' cmp #1\n bcc mu_frame','test_music.py','test_ntsc_uses_its_frequency_table_and_fifty_hz_timebase'),
 ('src/music.asm',' lda soundtime\n bne mu_render_fixed',' lda #0\n bne mu_render_fixed','test_music.py','test_tonal_effect_keeps_voice_one_until_it_finishes'),
 ('src/music.asm',' bcs mu_read_bad',' nop\n nop','test_music.py','test_truncated_bank_and_runtime_overrun_disable_playback'),
 ('tools/recover_amiga.py','disk[i:i+510]','disk[i:i+512]','test_music.py','test_custom_sector_payload_omits_only_the_two_byte_footer'),
]


def main():
    for file,old,new,testfile,test in CASES:
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'r'
            shutil.copytree(ROOT,target,ignore=shutil.ignore_patterns('.git','dist','__pycache__'))
            (target/'dist').mkdir()
            p=target/file;s=p.read_text()
            if s.count(old)!=1:raise SystemExit(f'Mutation is not uniquely applicable: {test}')
            p.write_text(s.replace(old,new,1))
            result=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-p',testfile,'-k',test],cwd=target,capture_output=True,text=True)
            if result.returncode==0:raise SystemExit('SURVIVED '+test)
            if 'FAIL: '+test not in result.stderr:raise SystemExit('INVALID KILL\n'+result.stderr)
            print('KILLED',test,flush=True)
    print(f'{len(CASES)} focused mutants killed')


if __name__=='__main__':main()
