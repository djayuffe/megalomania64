; --------------------------------------------------------------------------
; Diplomacy: truces. Key E (joystick FIRE+right) on a selected rival sector.
;  * A rival accepts when the human's strength >= the rival's strength.
;    strength = sum over owned sectors of people + weapons/2 + 4*tech.
;  * A truce lasts TRUCE_TICKS strategy ticks. While it holds the rival AI
;    never attacks human sectors. Attacking the partner voids the pact.
;  * Refusals, broken pacts and expiry start a TRUCE_COOL tick cool-down.
; State (truce[], truce_cool[]) is part of the v4 save snapshot.
; --------------------------------------------------------------------------
propose_truce:
 ldx selected
 lda owner,x
 cmp #2
 bcs pt_rival
 lda #<msg_truce_pick
 sta PTR
 lda #>msg_truce_pick
 sta PTR+1
 jsr message
 jmp beep_no
pt_rival:
 sta pt_faction
 tay
 lda truce,y
 beq pt_not_active
 lda #<msg_truce_have
 sta PTR
 lda #>msg_truce_have
 sta PTR+1
 jmp message
pt_not_active:
 lda truce_cool,y
 beq pt_evaluate
 lda #<msg_truce_cool
 sta PTR
 lda #>msg_truce_cool
 sta PTR+1
 jsr message
 jmp beep_no
pt_evaluate:
 jsr speech_question
 lda #1
 jsr calc_power
 lda pwr_lo
 sta pp_lo
 lda pwr_hi
 sta pp_hi
 lda pt_faction
 jsr calc_power
 lda pp_hi
 cmp pwr_hi
 bcc pt_refuse
 bne pt_accept
 lda pp_lo
 cmp pwr_lo
 bcc pt_refuse
pt_accept:
 ldy pt_faction
 lda #TRUCE_TICKS
 sta truce,y
 lda #<msg_truce_ok
 sta PTR
 lda #>msg_truce_ok
 sta PTR+1
 jsr message
 lda #4
 jsr speech_answer
 lda #SFX_TRUCE
 jmp sfx_play
pt_refuse:
 lda #5
 jsr speech_answer
 ldy pt_faction
 lda #TRUCE_COOL
 sta truce_cool,y
 lda #<msg_truce_no
 sta PTR
 lda #>msg_truce_no
 sta PTR+1
 jsr message
 jmp beep_no

; A = faction id -> pwr_hi:pwr_lo
calc_power:
 sta powf
 lda #0
 sta pwr_lo
 sta pwr_hi
 ldx #11
cp_loop:
 lda owner,x
 cmp powf
 bne cp_next
 lda people,x
 jsr pwr_add
 lda weapons,x
 lsr
 jsr pwr_add
 lda level,x
 asl
 asl
 jsr pwr_add
cp_next:
 dex
 bpl cp_loop
 rts
pwr_add:
 clc
 adc pwr_lo
 sta pwr_lo
 bcc pa_done
 inc pwr_hi
pa_done:
 rts

; Called by player_attack with A = owner of the target. Voids a pact if the
; attack will really go out (source garrison >= 8).
break_truce:
 ldx source
 ldy people,x
 cpy #8
 bcc bt_done
 cmp #2
 bcc bt_done
 tay
 lda truce,y
 beq bt_done
 lda #0
 sta truce,y
 lda #TRUCE_COOL
 sta truce_cool,y
 lda #<msg_truce_broken
 sta PTR
 lda #>msg_truce_broken
 sta PTR+1
 jsr message
 jsr beep_no
bt_done:
 rts

; Once per strategy tick.
diplo_tick:
 ldx #4
dt_loop:
 lda truce_cool,x
 beq dt_truce
 dec truce_cool,x
dt_truce:
 lda truce,x
 beq dt_next
 dec truce,x
 bne dt_next
 lda #TRUCE_COOL
 sta truce_cool,x
 lda #<msg_truce_end
 sta PTR
 lda #>msg_truce_end
 sta PTR+1
 stx dt_idx
 jsr message
 ldx dt_idx
dt_next:
 dex
 cpx #2
 bcs dt_loop
 rts

msg_truce_pick:   !text "SELECT A RIVAL SECTOR TO NEGOTIATE",0
msg_truce_have:   !text "A TRUCE IS ALREADY ACTIVE",0
msg_truce_cool:   !text "TALKS BLOCKED - TRY AGAIN LATER",0
msg_truce_ok:     !text "TRUCE AGREED - THEY WILL NOT ATTACK",0
msg_truce_no:     !text "REFUSED - YOU ARE TOO WEAK FOR A PACT",0
msg_truce_broken: !text "YOU BROKE THE TRUCE!",0
msg_truce_end:    !text "A TRUCE HAS ENDED",0
