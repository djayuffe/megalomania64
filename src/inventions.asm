; --------------------------------------------------------------------------
; Inventions: each epoch has a signature weapon. The HUD shows the current
; one; every research rank-up of a human sector announces
; "INVENTION: <WEAPON> MARK n".
; --------------------------------------------------------------------------
rank_up_notice:
 ldx simidx
 lda owner,x
 cmp #1
 bne ru_done
 ldy #0
ru_prefix:
 lda inv_prefix,y
 beq ru_prefix_done
 sta msgbuf,y
 iny
 bne ru_prefix
ru_prefix_done:
 lda epoch
 asl
 asl
 asl
 tax
ru_name:
 lda inv_names,x
 beq ru_mark
 sta msgbuf,y
 iny
 inx
 bne ru_name
ru_mark:
 ldx #0
ru_mark_loop:
 lda inv_mark,x
 beq ru_digit
 sta msgbuf,y
 iny
 inx
 bne ru_mark_loop
ru_digit:
 ldx simidx
 lda level,x
 clc
 adc #'0'
 sta msgbuf,y
 iny
 lda #0
 sta msgbuf,y
 lda #<msgbuf
 sta PTR
 lda #>msgbuf
 sta PTR+1
 jsr message
 lda #SFX_INVENT
 jsr sfx_play
 lda #7
 ldx #14
 jsr fx_flash          ; gold border pulse for a new invention
ru_done:
 ldx simidx
 rts

; Extra HUD lines: truce status (row 6), era weapon (row 12), source marker.
panel_extra:
 lda #1
 sta ink
 lda #30
 sta text_x
 lda #6
 sta text_y
 lda #<hud_pact
 sta PTR
 lda #>hud_pact
 sta PTR+1
 jsr print_text
 ldx selected
 lda owner,x
 cmp #2
 bcc pe_nopact
 tax
 lda truce,x
 sta value
 lda #35
 sta text_x
 lda #6
 sta text_y
 jsr print2
 jmp pe_arms
pe_nopact:
 lda #'-'
 ldx #35
 ldy #6
 jsr plot
 lda #'-'
 ldx #36
 ldy #6
 jsr plot
pe_arms:
 lda #30
 sta text_x
 lda #12
 sta text_y
 lda #<hud_arm
 sta PTR
 lda #>hud_arm
 sta PTR+1
 jsr print_text
 ldx #34
pe_blank:
 lda #32
 ldy #12
 jsr plot
 inx
 cpx #40
 bne pe_blank
 lda epoch
 asl
 asl
 asl
 sta pe_idx
 lda #34
 sta text_x
pe_name:
 ldx pe_idx
 lda inv_names,x
 beq draw_source_marker
 ldx text_x
 ldy #12
 jsr plot
 inc text_x
 inc pe_idx
 jmp pe_name

; Sprite 1 marks the army source sector (right of the cursor frame).
draw_source_marker:
 jsr colorize_ui
 ldx source
 lda sector_x,x
 asl
 asl
 asl
 clc
 adc #56
 sta $d002
 lda sector_y,x
 asl
 asl
 asl
 clc
 adc #58
 sta $d003
 rts

hud_pact:   !text "PACT:",0
hud_arm:    !text "ARM:",0
inv_prefix: !text "INVENTION: ",0
inv_mark:   !text " MARK ",0
inv_names:
 !text "CLUB",0,0,0,0
 !text "SPEAR",0,0,0
 !text "SWORD",0,0,0
 !text "BALLIS",0,0
 !text "XBOW",0,0,0,0
 !text "MUSKET",0,0
 !text "CANNON",0,0
 !text "TANK",0,0,0,0
 !text "MISSIL",0,0
 !text "LASER",0,0,0
