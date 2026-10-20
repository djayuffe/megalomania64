; Optional original-score SID arrangement. The two compact scores and PAL/NTSC
; frequency tables reside at $C400-$CFFF after the intro has released that RAM.
music_load:
 lda #0
 sta mu_ready
 lda #1
 sta music_hold
 lda #5
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
 cmp #$0c
 lbcs mu_load_end
 cmp #1
 lbcc mu_load_end
 sta ld_left+1
 cmp #1
 bne mu_copy_start
 lda ld_left
 cmp #4
 lbcc mu_load_end
mu_copy_start:
 lda #0
 sta PTR
 lda #$c4
 sta PTR+1
mu_copy:
 jsr ld_read
 bcs mu_load_end
 jsr ld_put
 bcs mu_load_end
 lda ld_left
 ora ld_left+1
 bne mu_copy
 lda ld_eof
 beq mu_load_end
 lda PTR
 sta mu_end
 lda PTR+1
 sta mu_end+1
 ldx #2
mu_check_ptr:
 lda $c501,x
 cmp #$c5
 bcc mu_load_end
 cmp mu_end+1
 bcc mu_check_min
 bne mu_load_end
 lda $c500,x
 cmp mu_end
 bcs mu_load_end
mu_check_min:
 lda $c501,x
 cmp #$c5
 bne mu_ptr_next
 lda $c500,x
 cmp #4
 bcc mu_load_end
mu_ptr_next:
 dex
 dex
 bpl mu_check_ptr
 lda #$ff
 sta mu_mode
 lda #1
 sta mu_ready
mu_load_end:
 jsr ld_close
 lda #0
 sta music_hold
 rts

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
 lda title_active
 cmp mu_mode
 beq mu_resume
 sta mu_mode
 jsr mu_restart
mu_resume:
 ldy #0
 ldx #0
mu_gates_on:
 cpx #0
 bne mu_gate_write
 lda soundtime
 bne mu_gate_next
 lda mu_cache
 sta $d400
 lda mu_cache+1
 sta $d401
mu_gate_write:
 lda mu_gates,y
 sta $d404,x                  ; re-gate one frame after a note, and resume after a digi
mu_gate_next:
 iny
 txa
 clc
 adc #7
 tax
 cpx #21
 bcc mu_gates_on
 lda mu_wait
 beq mu_event
 dec mu_wait
 lbne mu_return
mu_event:
 jsr mu_read
 lbcs mu_return
 lbeq mu_restart               ; four zero bytes are the bounded end-of-score sentinel
 sta mu_wait
 ldx #0
 ldy #0
mu_voices:
 sty mu_voice
 jsr mu_read
 lbcs mu_return
 beq mu_voice_next
 cmp #$ff
 beq mu_release
 sta mu_note
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
 cpx #0
 bne mu_freq_write
 sta mu_cache
 lda $c401,y
 sta mu_cache+1
 lda soundtime
 bne mu_voice_next
 lda mu_cache
mu_freq_write:
 sta $d400,x
 lda $c401,y
 sta $d401,x
 lda #0
 sta $d402,x
 lda #8
 sta $d403,x
 sta $d405,x
 lda #$a6
 sta $d406,x
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
 sta mu_gates,y
 and #$fe
 sta $d404,x
 jmp mu_voice_next
mu_release:
 lda #0
 ldy mu_voice
 sta mu_gates,y
 sta $d404,x
mu_voice_next:
 ldy mu_voice
 iny
 txa
 clc
 adc #7
 tax
 cpx #21
 lbcc mu_voices
mu_return:
 rts
mu_restart:
 lda title_active
 eor #1
 asl
 tax
 lda $c500,x
 sta mu_fetch+1
 lda $c501,x
 sta mu_fetch+2
 lda #0
 sta mu_wait
 sta mu_gates
 sta mu_gates+1
 sta mu_gates+2
 rts
mu_read:
 lda mu_fetch+2
 cmp mu_end+1
 bcc mu_fetch
 bne mu_read_bad
 lda mu_fetch+1
 cmp mu_end
 bcs mu_read_bad
mu_fetch:
 lda $c504                    ; self-modified sequential reader, never game zero page
 inc mu_fetch+1
 bne mu_read_ok
 inc mu_fetch+2
mu_read_ok:
 ora #0                      ; preserve byte's Z for the record decoder
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
