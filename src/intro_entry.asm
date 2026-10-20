; Original cards streamed to alternating VIC banks. Missing optional content falls
; back to the embedded title. A malformed/aborted sequence returns to the game.
intro_sequence:
 lda #0
 sta $c6                     ; discard the autostart RUN/RETURN queue before polling
 sta ic_skip
 sta ic_clock
 sta cr_phase
 sta cr_row
 sta ic_dirty
 sta ic_visible
 sta ic_hold
 sta ic_hold+1
 sta title_active
 sta music_hold
 lda #50
 ldx $02a6
 bne ic_pal_rate
 lda #60
ic_pal_rate:
 sta ic_rate
 lda #1
 sta ic_active
 sta title_bmp
 sta ic_bank
 sta ic_index
 lda vblank
 sta ic_vb
 lda $d015
 sta ic_sprites
 lda #0
 sta $d015
ic_next:
 lda ic_visible
 beq ic_filename
 lda ic_visible_mode
 cmp #2
 bcc ic_filename
ic_story_hold:
 jsr intro_poll              ; IEC masks IRQs: split-mode text needs a quiet display
 lbcs ic_finish
 lda ic_hold
 ora ic_hold+1
 bne ic_story_hold
 lda #$0b
 sta $d011                   ; blank only while the next story is loaded
ic_filename:
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
 lda ic_mode
 cmp #2
 bcs ic_keep_bank
 lda ic_bank
 eor #1
 sta ic_bank
ic_keep_bank:
 inc ic_index
 lda ic_index
 cmp #30
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
 php
 sei
 lda #0
 sta irq_stage
 sta ic_visible_mode
 lda #IRQ_LINE
 sta $d012
 sta irq_line
 plp
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

intro_entry_end:

; Two fixed-logo placements compensate for the VIC's character-row counter
; when changing YSCROLL at the text/bitmap split. Title score ends below $CAF8.
credit_logo_copy:
 php
 sei
 lda $01
 pha
 and #$fd
 sta $01
 ldx #0
cr_logo_pages:
 lda $f900,x
 sta $77c0,x
 lda $fa00,x
 sta $78c0,x
 lda $fb00,x
 sta $79c0,x
 lda $fc00,x
 sta $7ac0,x
 lda $fd00,x
 sta $7bc0,x
 lda $fe00,x
 sta $7cc0,x
 inx
 bne cr_logo_pages
 ldx #63
cr_logo_tail:
 lda $ff00,x
 sta $7dc0,x
 dex
 bpl cr_logo_tail
 ldx #199
cr_logo_screen:
 lda $cf20,x
 sta $52f8,x
 sta $cb20,x
 lda #0
 sta $cf20,x                ; prevent bitmap colour bytes becoming text glyphs
 dex
 cpx #$ff
 bne cr_logo_screen
 pla
 sta $01
 plp
 rts
intro_overlay_end:
