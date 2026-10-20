; Four virtual MOD channels on three SID oscillators. Channels 0/1 alternate on
; oscillator 1; 2/3 have dedicated voices. Banks use $C400-$D3FF, including RAM
; beneath I/O. Music never runs during a digi or IEC loading.
; A=0 title MUSIC, A=1 game MUSICG. File format MLM2.
music_load:
 sta mu_mode
 lda #0
 sta mu_ready
 lda #1
 sta music_hold
 lda mu_mode
 beq mu_title_name
 lda #6
 bne mu_open_name
mu_title_name:
 lda #5
mu_open_name:
 ldx #<mu_name
 ldy #>mu_name
 jsr ld_open
 lbcs mu_load_end
 ldx #0
mu_header:
 jsr ld_read
 lbcs mu_load_end
 cmp mu_magic,x
 lbne mu_load_end
 inx
 cpx #4
 bcc mu_header
 jsr ld_read
 lbcs mu_load_end
 sta ld_left
 jsr ld_read
 lbcs mu_load_end
 cmp #$11
 lbcs mu_load_end
 cmp #1
 lbcc mu_load_end
 sta ld_left+1
 cmp #$10
 bne mu_minimum
 lda ld_left
 lbne mu_load_end
mu_minimum:
 lda ld_left+1
 cmp #1
 bne mu_copy_start
 lda ld_left
 cmp #3
 lbcc mu_load_end
mu_copy_start:
 lda #0
 sta PTR
 lda #$c4
 sta PTR+1
mu_copy:
 jsr ld_read
 bcs mu_load_end
 jsr mu_store
 lda ld_left
 ora ld_left+1
 bne mu_copy
 lda ld_eof
 beq mu_load_end
 lda PTR
 sta mu_end
 lda PTR+1
 sta mu_end+1
 jsr mu_restart
 lda #1
 sta mu_ready
mu_load_end:
 jsr ld_close
 lda #0
 sta music_hold
 rts

mu_store:
 jmp ld_put

original_music_tick:
 lda $02a6
 bne mu_frame
 inc mu_ntsc
 lda mu_ntsc
 cmp #6
 bcc mu_frame
 lda #0
 sta mu_ntsc
 rts
mu_frame:
 lda mu_wait
 beq mu_event
 dec mu_wait
 bne mu_render_all
mu_event:
 jsr mu_read
 lbcs mu_return
 bne mu_have_time
 jsr mu_restart
 jmp mu_render_all
mu_have_time:
 sta mu_wait
 jsr mu_read
 lbcs mu_return
 cmp #16
 lbcs mu_read_bad
 sta mu_mask
 ldx #0
mu_events:
 lsr mu_mask
 bcc mu_event_next
 jsr mu_read
 lbcs mu_return
 beq mu_amplitude
 cmp #$ff
 beq mu_off
 sta mu_notes,x
 lda #1
 sta mu_pending,x
 bne mu_amplitude
mu_off:
 lda #0
 sta mu_notes,x
mu_amplitude:
 jsr mu_read
 lbcs mu_return
 cmp #16
 lbcs mu_read_bad
 sta mu_amps,x
mu_event_next:
 inx
 cpx #4
 bcc mu_events
mu_render_all:
 lda soundtime
 bne mu_render_fixed
 ldy #0
 lda mu_notes
 beq mu_choose_one
 lda mu_amps
 beq mu_choose_one
 lda mu_notes+1
 beq mu_shared_ready
 lda mu_amps+1
 beq mu_shared_ready
 inc mu_phase
 lda mu_phase
 and #1
 tay
 jmp mu_shared_ready
mu_choose_one:
 iny
mu_shared_ready:
 ldx #0
 jsr mu_render
mu_render_fixed:
 ldx #7
 ldy #2
 jsr mu_render
 ldx #14
 ldy #3
 jsr mu_render
mu_return:
 rts

; X=SID register offset, Y=virtual channel. Restore the complete oscillator state
; every frame, including ADSR/pulse/waveform after UI effects and digital speech.
mu_render:
 sty mu_voice
 lda mu_notes,y
 beq mu_silent
 sta mu_note
 lda mu_amps,y
 beq mu_silent
 asl
 asl
 asl
 asl
 ora #6
 sta $d406,x
 lda #$08
 sta $d405,x
 lda mu_note
 and #$c0
 cmp #$c0
 bne mu_sustained
 lda #0
 sta $d406,x                  ; drum/cymbal noise must decay, never drone at sustain
 lda #6
 sta $d405,x
mu_sustained:
 lda #0
 sta $d402,x
 lda #8
 sta $d403,x
 lda mu_note
 and #$3f
 asl
 tay
 lda $02a6
 bne mu_pitch
 tya
 ora #$80
 tay
mu_pitch:
 lda $c400,y
 sta $d400,x
 lda $c401,y
 sta $d401,x
 lda mu_note
 lsr
 lsr
 lsr
 lsr
 lsr
 lsr
 tay
 lda mu_wave,y
 ldy mu_voice
 pha
 lda mu_pending,y
 beq mu_gate_on
 lda #0
 sta mu_pending,y
 pla
 and #$fe
 sta $d404,x
 rts
mu_gate_on:
 pla
 sta $d404,x
 rts
mu_silent:
 lda #0
 sta $d404,x
 rts

mu_restart:
 lda #0
 sta mu_fetch+1
 sta mu_wait
 sta mu_ntsc
 ldx #3
mu_clear:
 sta mu_notes,x
 sta mu_amps,x
 sta mu_pending,x
 dex
 bpl mu_clear
 lda #$c5
 sta mu_fetch+2
 rts
mu_read:
 lda mu_fetch+2
 cmp mu_end+1
 bcc mu_read_ram
 bne mu_read_bad
 lda mu_fetch+1
 cmp mu_end
 bcs mu_read_bad
mu_read_ram:
 lda $01
 pha
 and #$f8
 sta $01
mu_fetch:
 lda $c500
 sta mu_value
 pla
 sta $01
 inc mu_fetch+1
 bne mu_read_ok
 inc mu_fetch+2
mu_read_ok:
 lda mu_value
 clc
 rts
mu_read_bad:
 lda #0
 sta mu_ready
 sta $d404
 sta $d40b
 sta $d412
 sec
 rts
music_code_end:
