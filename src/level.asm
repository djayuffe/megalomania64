; Optional original island atlas tile, loaded per island into free sprites 4/5.
; These 128 bytes never overwrite the resident speech or the game's army sprites.
level_card:
 lda cards_on
 lbne lc_begin
 rts
lc_begin:
 lda #0
 sta lc_ok
 lda campaign_island
 clc
 adc #1
 ldx #$30
lc_tens:
 cmp #10
 bcc lc_ones
 sec
 sbc #10
 inx
 jmp lc_tens
lc_ones:
 stx lc_name+3
 clc
 adc #$30
 sta lc_name+4
 lda #1
 sta title_bmp
 sta ic_active
 lda #0
 sta ic_skip
 lda vblank
 sta ic_vb
 lda #5
 ldx #<lc_name
 ldy #>lc_name
 jsr ld_open
 lbcs lc_done
 ldx #0
lc_magic_loop:
 jsr ld_read
 lbcs lc_done
 cmp lc_magic,x
 lbne lc_done
 inx
 cpx #4
 bcc lc_magic_loop
 ldx #0
lc_colors_read:
 jsr ld_read
 lbcs lc_done
 cmp #16
 lbcs lc_done
 sta lc_colors,x
 inx
 cpx #3
 bcc lc_colors_read
 ldx #0
lc_data:
 jsr ld_read
 lbcs lc_done
 sta $3400,x
 inx
 cpx #128
 bcc lc_data
 lda ld_eof
 lbeq lc_done
 lda #1
 sta lc_ok
lc_done:
 jsr ld_close
 lda lc_ok
 lbeq lc_exit
 jsr lc_screen
 ldy #8
lc_save:
 ldx lc_regs,y
 lda $d000,x
 sta lc_saved,y
 dey
 bpl lc_save
 ldx #3
lc_position_save:
 lda $d008,x
 sta lc_pos,x
 dex
 bpl lc_position_save
 lda $07fc
 sta lc_ptr
 lda $07fd
 sta lc_ptr+1
 lda #$d0
 sta $07fc
 lda #$d1
 sta $07fd
 lda #136
 sta $d008
 lda #184
 sta $d00a
 lda #140
 sta $d009
 sta $d00b
 lda $d010
 and #$cf
 sta $d010
 lda $d017
 ora #$30
 sta $d017
 lda $d01d
 ora #$30
 sta $d01d
 lda $d01c
 ora #$30
 sta $d01c
 lda lc_colors
 sta $d025
 lda lc_colors+1
 sta $d02b
 sta $d02c
 lda lc_colors+2
 sta $d026
 lda #$30
 sta $d015
 lda #120
 sta ic_hold
 lda #0
 sta ic_hold+1
lc_wait:
 jsr intro_poll
 bcs lc_restore
 lda ic_hold
 ora ic_hold+1
 bne lc_wait
lc_restore:
 ldy #8
lc_restore_regs:
 ldx lc_regs,y
 lda lc_saved,y
 sta $d000,x
 dey
 bpl lc_restore_regs
 ldx #3
lc_restore_pos:
 lda lc_pos,x
 sta $d008,x
 dex
 bpl lc_restore_pos
 lda lc_ptr
 sta $07fc
 lda lc_ptr+1
 sta $07fd
 jsr draw_static
 jsr draw_all
 jsr draw_panel
 jsr draw_score
 jsr draw_cursor
 lda #<msg_start
 sta PTR
 lda #>msg_start
 sta PTR+1
 jsr message
lc_exit:
 lda #0
 sta title_bmp
 sta ic_active
 rts
; Clear exactly the 1000 visible characters, preserving all eight sprite pointers.
lc_screen:
 ldx #0
lc_clear:
 lda #32
 sta SCR,x
 sta SCR+256,x
 sta SCR+512,x
 sta SCR+744,x
 lda #1
 sta COL,x
 sta COL+256,x
 sta COL+512,x
 sta COL+744,x
 inx
 bne lc_clear
 jsr print_island_name
 ldx #10
 lda #32
lc_remove_header:
 sta SCR+20,x
 dex
 bpl lc_remove_header
 lda #14
 sta text_x
 lda #7
 sta text_y
 jsr print_text
 lda #1
 sta ink
 lda #12
 sta text_x
 lda #5
 sta text_y
 lda #<lc_caption
 sta PTR
 lda #>lc_caption
 sta PTR+1
 jsr print_text
 lda campaign_island
 clc
 adc #1
 sta value
 lda #19
 sta text_x
 lda #6
 sta text_y
 jsr print2
 lda #15
 sta text_x
 lda #8
 sta text_y
 lda #<lc_epoch
 sta PTR
 lda #>lc_epoch
 sta PTR+1
 jsr print_text
 lda epoch
 clc
 adc #1
 sta value
 lda #21
 sta text_x
 lda #8
 sta text_y
 jsr print2
 rts
