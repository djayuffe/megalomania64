; Eight original voices, 4-bit / 4 kHz. Resident RAM: $4C80-$7FFF + $E000-$FFF9.
; Index entries are (address, nibble count); validate the complete contiguous bank
; before enabling it. Hardware vectors at $FFFA-$FFFF are never sample storage.
speech_load:
 lda $d015
 sta sp_sprites
 lda #0
 sta $d015
 lda #1
 sta title_bmp
 sta music_hold
 lda #<sp_msg
 sta PTR
 lda #>sp_msg
 sta PTR+1
 jsr message
 lda #0
 sta sp_ready
 lda #6
 ldx #<sp_name
 ldy #>sp_name
 jsr ld_open
 lbcs sp_load_bad
 ldx #0
sp_magic_loop:
 jsr ld_read
 lbcs sp_load_bad
 cmp sp_magic,x
 lbne sp_load_bad
 inx
 cpx #4
 bcc sp_magic_loop
 ldx #0
sp_index_loop:
 jsr ld_read
 lbcs sp_load_bad
 sta sp_index,x
 inx
 cpx #32
 bcc sp_index_loop
 jsr speech_validate
 lbcs sp_load_bad
 lda #$80
 sta PTR
 sta ld_left
 lda #$4c
 sta PTR+1
 lda #$33
 sta ld_left+1
 jsr ld_unpack
 lbcs sp_load_bad
 lda #0
 sta PTR
 lda #$e0
 sta PTR+1
 lda #$fa
 sta ld_left
 lda #$1f
 sta ld_left+1
 jsr ld_unpack
 lbcs sp_load_bad
 lda ld_eof
 lbeq sp_load_bad
 lda #1
 sta sp_ready
sp_load_bad:
 jsr ld_close
 lda sp_sprites
 sta $d015
 lda #0
 sta title_bmp
 sta music_hold
 lda #<msg_start
 sta PTR
 lda #>msg_start
 sta PTR+1
 jsr message
 rts

speech_validate:
 lda #$80
 sta sp_end
 lda #$4c
 sta sp_end+1
 ldx #0
sp_validate_loop:
 lda sp_index,x
 cmp sp_end
 lbne sp_invalid
 lda sp_index+1,x
 cmp sp_end+1
 lbne sp_invalid
 lda sp_index+2,x
 and #1
 lbne sp_invalid
 lda sp_index+2,x
 ora sp_index+3,x
 lbeq sp_invalid
 lda sp_index+3,x
 cmp #$40
 lbcs sp_invalid
 lsr
 sta sp_bytes+1
 lda sp_index+2,x
 ror
 sta sp_bytes
 lda sp_end+1
 sta sp_oldhi
 clc
 lda sp_end
 adc sp_bytes
 sta sp_end
 lda sp_end+1
 adc sp_bytes+1
 lbcs sp_invalid
 sta sp_end+1
 lda sp_oldhi
 cmp #$80
 bcs sp_check_top
 lda sp_end+1
 cmp #$80
 bcc sp_check_top
 clc
 adc #$60
 sta sp_end+1
sp_check_top:
 lda sp_end+1
 cmp #$ff
 bcc sp_validate_next
 lda sp_end
 cmp #$fb
 bcs sp_invalid
sp_validate_next:
 inx
 inx
 inx
 inx
 cpx #32
 lbcc sp_validate_loop
 clc
 rts
sp_invalid:
 sec
 rts

speech_play:
 cmp #8
 bcs sp_play_done
 sta sp_id
 lda sp_ready
 beq sp_play_done
 jsr sample_stop
 jsr sample_mute
 lda sp_id
 asl
 asl
 tax
 lda sp_index,x
 sta smp_rd+1
 lda sp_index+1,x
 sta smp_rd+2
 lda sp_index+2,x
 sta smp_left
 lda sp_index+3,x
 sta smp_left+1
 lda #0
 sta smp_half
 lda #1
 sta smp_speech
 jmp sm_start
sp_play_done:
 rts

; X=SFX id. Preserve X; carry means the speech handled this sound.
speech_event:
 lda sp_ready
 beq sp_event_none
 lda sp_event,x
 cmp #$ff
 beq sp_event_none
 sta sp_wanted
 lda smp_left
 ora smp_left+1
 beq sp_event_go
 lda sfx_prio,x
 cmp smp_prio
 bcc sp_event_busy
sp_event_go:
 lda sfx_prio,x
 sta smp_prio
 lda sfx_smp,x
 cmp #$ff
 beq sp_event_voice
 jsr sfx_sample              ; retain explosion/grunt/fanfare before the spoken reaction
 bcc sp_event_voice
 lda sp_wanted
 sta sp_queue
 sec
 rts
sp_event_voice:
 txa
 pha
 lda sp_wanted
 jsr speech_play
 pla
 tax
sp_event_busy:
 sec
 rts
sp_event_none:
 clc
 rts
speech_question:
 lda #3
 jmp speech_play
speech_answer:
 sta sp_wanted
 lda sp_ready
 beq sp_answer_done
 lda smp_speech
 beq sp_answer_now
 lda sp_id
 cmp #3
 bne sp_answer_now
 lda sp_wanted
 sta sp_queue
 rts
sp_answer_now:
 lda sp_wanted
 jmp speech_play
sp_answer_done:
 rts
sample_finished:
 lda sp_queue
 pha
 jsr sample_stop
 pla
 cmp #8
 bcs sp_answer_done
 jmp speech_play
