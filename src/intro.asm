; Original cards streamed to alternating VIC banks. Missing optional content falls
; back to the embedded title. A malformed/aborted sequence returns to the game.
intro_sequence:
 lda #0
 sta $c6                     ; discard the autostart RUN/RETURN queue before polling
 sta ic_skip
 sta ic_dirty
 sta ic_visible
 sta ic_hold
 sta ic_hold+1
 sta title_active
 lda #1
 sta ic_active
 sta title_bmp
 sta music_hold
 sta ic_bank
 sta ic_index
 lda vblank
 sta ic_vb
 lda $d015
 sta ic_sprites
 lda #0
 sta $d015
ic_next:
 lda ic_index
 ldx #$30
ic_tens:
 cmp #10
 bcc ic_ones
 sec
 sbc #10
 inx
 jmp ic_tens
ic_ones:
 stx ic_name+5
 clc
 adc #$30
 sta ic_name+6
 lda #7
 ldx #<ic_name
 ldy #>ic_name
 jsr ic_load
 bcs ic_finish
ic_wait:
 jsr intro_poll
 bcs ic_finish
 lda ic_hold
 ora ic_hold+1
 bne ic_wait
 jsr ic_flip
 lda ic_time
 sta ic_hold
 lda ic_time+1
 sta ic_hold+1
 lda #1
 sta ic_visible
 lda ic_bank
 eor #1
 sta ic_bank
 inc ic_index
 lda ic_index
 cmp #21
 bcc ic_next
ic_last_wait:
 jsr intro_poll
 bcs ic_finish
 lda ic_hold
 ora ic_hold+1
 bne ic_last_wait
ic_finish:
 lda #0
 sta ic_active
 lda ic_dirty
 beq ic_exit
 lda #$0b
 sta $d011
 lda #0
 sta ic_bank
 lda #5
 ldx #<ic_title
 ldy #>ic_title
 jsr ic_load
 bcc ic_exit
 lda #1
 sta ic_skip
ic_exit:
 lda #0
 sta title_bmp
 sta music_hold
 sta title_active
 lda $dd00
 and #$fc
 ora #3
 sta $dd00
 lda #$1b
 sta $d011
 lda #$18
 sta $d016
 lda #$1e
 sta $d018
 lda #6
 sta $d020
 sta $d021
 lda ic_sprites
 sta $d015
 lda ic_skip
 bne ic_return_skip
 clc
 rts
ic_return_skip:
 sec
 rts

; Called after each disk byte, and while waiting. Frame subtraction handles wrap.
intro_poll:
 lda ic_active
 beq ic_poll_ok
 lda ic_skip
 bne ic_poll_abort
 lda vblank
 sec
 sbc ic_vb
 beq ic_poll_ok
 tax
 lda vblank
 sta ic_vb
ic_tick:
 lda ic_hold
 ora ic_hold+1
 beq ic_keys
 lda ic_hold
 bne ic_tick_low
 dec ic_hold+1
ic_tick_low:
 dec ic_hold
 dex
 bne ic_tick
ic_keys:
 lda ld_opened
 beq ic_keyboard
 jsr $ffcc                    ; GETIN otherwise reads the selected disk channel!
 jsr KGETIN
 pha
 ldx #2
 jsr $ffc6
 pla
 jmp ic_key_ready
ic_keyboard:
 jsr KGETIN
ic_key_ready:
 bne ic_poll_abort
 lda joy_raw
 and #16
 beq ic_poll_abort
ic_poll_ok:
 clc
 rts
ic_poll_abort:
 lda #1
 sta ic_skip
 sec
 rts

ic_load:
 jsr ld_open
 lbcs ic_load_bad
 ldx #0
ic_magic:
 jsr ld_read
 lbcs ic_load_bad
 cmp ic_signature,x
 lbne ic_load_bad
 inx
 cpx #4
 bcc ic_magic
 jsr ld_read
 lbcs ic_load_bad
 cmp #2
 lbcs ic_load_bad
 sta ic_mode
 jsr ld_read
 lbcs ic_load_bad
 cmp #16
 lbcs ic_load_bad
 sta ic_bg
 jsr ld_read
 lbcs ic_load_bad
 sta ic_time
 jsr ld_read
 lbcs ic_load_bad
 sta ic_time+1
 ora ic_time
 lbeq ic_load_bad
 lda #0
 sta ic_segment
 lda ic_bank
 bne ic_segments
 lda #1
 sta ic_dirty                 ; even a failed unpack may overwrite the embedded bitmap
ic_segments:
 lda ic_bank
 asl
 clc
 adc ic_bank
 clc
 adc ic_segment
 tax
 lda ic_dest_lo,x
 sta PTR
 lda ic_dest_hi,x
 sta PTR+1
 ldx ic_segment
 lda ic_size_lo,x
 sta ld_left
 lda ic_size_hi,x
 sta ld_left+1
 jsr ld_unpack
 bcs ic_load_bad
 inc ic_segment
 lda ic_segment
 cmp #3
 bcc ic_segments
 lda ld_eof
 beq ic_load_bad              ; reject trailing bytes, not just a valid prefix
 jsr ld_close
 clc
 rts
ic_load_bad:
 jsr ld_close
 lda ic_visible
 beq ic_no_skip
 lda #1
 sta ic_skip
ic_no_skip:
 sec
 rts

ic_flip:
 lda #$0b
 sta $d011
 ldx ic_bank
 lda ic_color_hi,x
 sta PTR+1
 lda #0
 sta PTR
 sta CPTR
 lda #$d8
 sta CPTR+1
 ldx #4
 ldy #0
ic_colors:
 lda (PTR),y
 sta (CPTR),y
 iny
 bne ic_colors
 inc PTR+1
 inc CPTR+1
 dex
 bne ic_colors
 ldx ic_bank
 lda $dd00
 and #$fc
 ora ic_vic,x
 sta $dd00
 lda ic_d018,x
 sta $d018
 lda ic_mode
 beq ic_hires
 lda #$18
 bne ic_d016
ic_hires:
 lda #$08
ic_d016:
 sta $d016
 lda ic_bg
 sta $d021
 lda #0
 sta $d020
 lda #$3b
 sta $d011
ic_displayed:
 rts
