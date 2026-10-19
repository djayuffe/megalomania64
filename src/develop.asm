; --------------------------------------------------------------------------
; U = develop: spend the selected human sector's ore on the most useful
; next step. Priority: laboratory, factory, first miners, mine upgrade,
; scientists, light fortification, weapons, more miners, heavy fortification.
; Each step re-uses the normal build routines, so cost rules stay identical.
; --------------------------------------------------------------------------
develop:
 ldx selected
 lda owner,x
 cmp #1
 lbne denied
 lda buildings,x             ; 1 laboratory
 and #2
 bne dv_factory
 lda ore,x
 cmp #6
 bcc dv_factory
 jmp build_lab
dv_factory:
 lda buildings,x
 and #4
 bne dv_miners
 lda ore,x
 cmp #10
 bcc dv_miners
 jmp build_factory
dv_miners:
 lda miners,x
 cmp #2
 bcs dv_mine
 jsr can_assign
 bcc dv_mine
 jmp add_miner
dv_mine:
 ldx selected
 lda minegrade,x
 cmp #2
 bcs dv_scientists
 lda ore,x
 cmp #8
 bcc dv_scientists
 jmp upgrade_mine
dv_scientists:
 ldx selected
 lda buildings,x
 and #2
 beq dv_fort1
 lda labs,x
 cmp #2
 bcs dv_fort1
 jsr can_assign
 bcc dv_fort1
 jmp add_lab
dv_fort1:
 ldx selected
 lda fort,x
 cmp #3
 bcs dv_weapon
 lda ore,x
 cmp #12
 bcc dv_weapon
 jmp make_fort
dv_weapon:
 ldx selected
 lda buildings,x
 and #4
 beq dv_miners2
 lda weapons,x
 cmp #30
 bcs dv_miners2
 lda ore,x
 cmp #4
 bcc dv_miners2
 jmp make_weapon
dv_miners2:
 ldx selected
 lda miners,x
 cmp #4
 bcs dv_fort2
 jsr can_assign
 bcc dv_fort2
 jmp add_miner
dv_fort2:
 ldx selected
 lda fort,x
 cmp #9
 bcs dv_none
 lda ore,x
 cmp #12
 bcc dv_none
 jmp make_fort
dv_none:
 jmp denied

; Keys that are not part of the original v3 command set.
key_extra:
 cmp #'E'
 bne ke_u
 jsr propose_truce
 jmp draw_panel
ke_u:
 cmp #'U'
 bne ke_u2
 jsr develop
 jmp draw_panel
ke_u2:
 cmp #'1'
 bcc ke_invalid
 cmp #'4'
 bcs ke_invalid
 sec
 sbc #'1'
 sta speed
 jsr set_speed
 jsr draw_speed
 ldx speed
 lda spd_msg_lo,x
 sta PTR
 lda spd_msg_hi,x
 sta PTR+1
 jmp message
ke_invalid:
 jmp key_invalid

; frames_per_tick = table[speed], PAL/NTSC aware (slow/normal/fast).
set_speed:
 ldx speed
 lda $02a6                   ; KERNAL: PAL=1, NTSC=0
 beq ss_ntsc
 lda speed_pal,x
 bne ss_store
ss_ntsc:
 lda speed_ntsc,x
ss_store:
 sta frames_per_tick
 rts

draw_speed:
 lda speed
 clc
 adc #'1'
 sta spd_msg+6
 lda #1
 sta ink
 lda #33
 sta text_x
 lda #0
 sta text_y
 lda #<spd_msg
 sta PTR
 lda #>spd_msg
 sta PTR+1
 jmp print_text

speed:       !byte 1
speed_pal:   !byte 40,24,16
speed_ntsc:  !byte 48,29,19
spd_msg_lo:  !byte <msg_spd0,<msg_spd1,<msg_spd2
spd_msg_hi:  !byte >msg_spd0,>msg_spd1,>msg_spd2
