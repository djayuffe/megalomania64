; --------------------------------------------------------------------------
; Port 2 joystick decoder. Input is `joy_raw` (active-low bits 0-4:
; up, down, left, right, fire) sampled by the raster IRQ.
;
;   no FIRE   stick edge          -> W / S / A / D (selection moves)
;   FIRE tap  (press + release)   -> ENTER on own land (set army source),
;                                    X raid otherwise; C / N / SPACE on
;                                    victory / defeat / pause screens
;   FIRE held + direction chord (stable CHORD_FRAMES frames):
;        up T heavy assault       down U develop sector
;        left Q doctrine          right E propose truce
;        up+left H send troops    up+right Y auto-arms
;        down+left Z auto-fort    down+right SPACE pause
; Returns the equivalent keyboard code in A (0 = nothing).
; --------------------------------------------------------------------------
read_joystick:
 lda joy_raw
 and #31
 sta joycur
 ldx joylast                 ; X = previous sample
 sta joylast
 and #16
 beq jy_fire_now             ; FIRE is down this frame
 txa
 and #16
 bne jy_dirs                 ; was up, is up: plain stick
 lda joyfire                 ; FIRE just released
 pha
 lda #0
 sta joyfire
 sta joycount
 pla
 cmp #1
 bne jy_none                 ; a chord already did something
 jmp joy_fire_action
jy_none:
 lda #0
 rts
jy_fire_now:
 txa
 and #16
 beq jy_fire_held
 lda #1                      ; press edge
 sta joyfire
 lda #0
 sta joycount
 lda #15
 sta joychord
 lda #0
 rts
jy_fire_held:
 lda joycur
 and #15
 cmp #15
 beq jy_chord_idle
 ldy #2
 sty joyfire                 ; any stick movement cancels the FIRE tap
 cmp joychord
 beq jy_chord_same
 sta joychord                ; new pattern: restart debounce
 lda #1
 sta joycount
 lda #0
 rts
jy_chord_idle:
 sta joychord
 lda #0
 sta joycount
 rts
jy_chord_same:
 lda joycount
 cmp #CHORD_FRAMES
 bcs jy_none                 ; already fired for this pattern
 inc joycount
 lda joycount
 cmp #CHORD_FRAMES
 bne jy_none
 ldx joychord
 lda joy_chord_key,x
 rts                         ; 0 for patterns without a command
jy_dirs:
 lda joycur
 eor #15
 and #15                     ; pressed now (active high)
 sta joyedge
 txa
 and #15                     ; previous (active low: set = not pressed)
 and joyedge                 ; = newly pressed directions
 beq jy_none
 lsr
 bcs jy_up
 lsr
 bcs jy_down
 lsr
 bcs jy_left
 lda #'D'
 rts
jy_up:
 lda #'W'
 rts
jy_down:
 lda #'S'
 rts
jy_left:
 lda #'A'
 rts

joy_fire_action:
 lda state
 beq jfa_game
 cmp #1
 bne jfa_over
 lda #' '                    ; paused: resume
 rts
jfa_over:
 cmp #2
 bne jfa_new
 lda #'C'                    ; island won: next island
 rts
jfa_new:
 lda #'N'                    ; defeat / campaign won: new campaign
 rts
jfa_game:
 ldx selected
 lda owner,x
 cmp #1
 bne jfa_attack
 lda #13
 rts
jfa_attack:
 lda #'X'
 rts

; index = direction nibble (active low: bit0 up, bit1 down, bit2 left, bit3 right)
joy_chord_key:
 !byte 0,0,0,0, 0,' ',  'Y',  'E'
 !byte 0,'Z','H','Q', 0,'U','T',  0
