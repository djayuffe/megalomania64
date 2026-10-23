; Independent NGSELECT entry. Reuses audited intro renderers in its private
; executable; never patches the frozen entry PRG or retains preview RAM in game.
* = $1000
sel_start:
 sei
 cld
 ldx #$ff
 txs
 lda #$36
 sta $01
 lda #0
 sta $9d
 sta sel_mode
 sta sel_index
 sta ic_active
 sta title_active
 lda #1
 sta title_bmp
 lda #$ff
 sta sel_tens
 sta sel_joy
 lda #1
 sta $cc
 jsr irq_install
 lda #0
 jsr music_load
sel_menu:
 lda #0
 sta ic_active
 sta ic_visible_mode
 sta irq_stage
 sta $d015
 lda #IRQ_LINE
 sta $d012
 lda $dd00
 and #$fc
 ora #3
 sta $dd00
 lda #$1b
 sta $d011
 lda #8
 sta $d016
 lda #$14
 sta $d018
 lda #6
 sta $d020
 sta $d021
 lda #147
 jsr $ffd2
 lda #7
 sta $0286
 lda #<sel_title
 ldy #>sel_title
 jsr sel_print
 lda sel_mode
 lbeq sel_intro_label
 lda #<sel_game_text
 ldy #>sel_game_text
 lbne sel_label
sel_intro_label:
 lda #<sel_intro_text
 ldy #>sel_intro_text
sel_label:
 jsr sel_print
 lda sel_index
 clc
 adc #1
 jsr sel_number
 lda #<sel_controls
 ldy #>sel_controls
 jsr sel_print
sel_wait:
 jsr $ffe4
 lbne sel_input
 lda joy_raw
 cmp sel_joy
 lbeq sel_wait
 sta sel_joy
 and #16
 lbeq sel_fire
 lda sel_joy
 and #5
 cmp #5
 lbne sel_left
 lda sel_joy
 and #10
 cmp #10
 lbne sel_right
 jmp sel_wait
sel_fire:
 lda #13
 lbne sel_input
sel_left:
 lda #'A'
 lbne sel_input
sel_right:
 lda #'D'
sel_input:
 cmp #'I'
 lbeq sel_intro
 cmp #'G'
 lbeq sel_game
 cmp #'A'
 lbeq sel_previous
 cmp #'D'
 lbeq sel_next
 cmp #13
 lbeq sel_activate
 cmp #'0'
 lbcc sel_wait
 cmp #':'
 lbcs sel_wait
 sec
 sbc #'0'
 ldx sel_tens
 cpx #$ff
 lbne sel_second
 cmp #3
 lbcs sel_wait
 sta sel_tens
 jmp sel_wait
sel_second:
 cpx #0
 lbeq sel_digit_done
sel_digit_add:
 clc
 adc #10
 dex
 lbne sel_digit_add
sel_digit_done:
 tax
 lda #$ff
 sta sel_tens
 txa
 lbeq sel_wait
 sec
 sbc #1
 cmp #29
 lbcs sel_wait
 ldx sel_mode
 lbeq sel_digit_valid
 cmp #28
 lbcs sel_wait
sel_digit_valid:
 sta sel_index
 jmp sel_menu
sel_intro:
 lda #0
 lbeq sel_change_mode
sel_game:
 lda #1
sel_change_mode:
 sta sel_mode
 lda #0
 sta sel_index
 lda #$ff
 sta sel_tens
 jmp sel_menu
sel_previous:
 lda sel_index
 lbne sel_decrement
 lda #29
 sec
 sbc sel_mode
sel_decrement:
 sec
 sbc #1
 sta sel_index
 jmp sel_menu
sel_next:
 inc sel_index
 lda #29
 sec
 sbc sel_mode
 cmp sel_index
 lbne sel_next_done
 lda #0
 sta sel_index
sel_next_done:
 jmp sel_menu
sel_activate:
 lda #$ff
 sta sel_tens
 lda sel_mode
 lbeq sel_preview
 lda #'S'
 sta $02f0
 lda #'E'
 sta $02f1
 lda #'L'
 sta $02f2
 lda sel_index
 sta $02f3
 eor #$ff
 sta $02f4
 jsr native_start
 lda #0
 sta $02f0
 jmp sel_error
sel_preview:
 lda #0
 sta $c6
 sta ic_skip
 sta ic_active
 sta ic_visible
 sta ic_clock
 lda #1
 sta ic_bank
 sta music_hold
 lda #$0b
 sta $d011
 ldx sel_index
 lda sel_bases,x
 cmp sel_index
 lbeq sel_only_scene
 jsr sel_load
 lbcs sel_error
sel_only_scene:
 lda sel_index
 jsr sel_load
 lbcs sel_error
 jsr ic_flip
 lda ic_time
 sta ic_hold
 lda ic_time+1
 sta ic_hold+1
 lda vblank
 sta ic_vb
 lda #50
 ldx $02a6
 lbne sel_rate
 lda #60
sel_rate:
 sta ic_rate
 lda #0
 sta music_hold
 sta $c6
sel_release_fire:
 lda joy_raw
 and #16
 lbeq sel_release_fire
 lda #1
 sta ic_active
sel_preview_wait:
 jsr intro_poll
 lbcc sel_preview_wait
 jmp sel_menu
sel_error:
 lda #0
 sta ic_active
 sta music_hold
 jsr sel_menu_error
 jmp sel_menu
sel_menu_error:
 lda #2
 sta $d020
 lda #0
 sta $c6
sel_error_wait:
 jsr $ffe4
 lbeq sel_error_wait
 rts
sel_load:
 clc
 adc #1
 ldx #$30
sel_name_tens:
 cmp #10
 lbcc sel_name_ones
 sec
 sbc #10
 inx
 lbne sel_name_tens
sel_name_ones:
 stx ic_name+5
 clc
 adc #$30
 sta ic_name+6
 lda #7
 ldx #<ic_name
 ldy #>ic_name
 jmp ic_load
sel_number:
 ldx #$30
sel_number_tens:
 cmp #10
 lbcc sel_number_ones
 sec
 sbc #10
 inx
 lbne sel_number_tens
sel_number_ones:
 pha
 txa
 jsr $ffd2
 pla
 clc
 adc #$30
 jmp $ffd2
sel_print:
 sta $fb
 sty $fc
 ldy #0
sel_print_loop:
 lda ($fb),y
 lbeq sel_print_done
 jsr $ffd2
 iny
 lbne sel_print_loop
sel_print_done:
 rts
sel_mode: !byte 0
sel_index: !byte 0
sel_tens: !byte $ff
sel_joy: !byte $ff
sel_bases: !fill 29,0
sel_title: !text "MEGA-LO-MANIA 64",13,"SCENE / ISLAND SELECTOR",13,13,0
sel_intro_text: !text "INTRO PREVIEW 01-29: ",0
sel_game_text: !text "GAME ISLAND 01-28: ",0
sel_controls: !text 13,13,"I INTRO   G GAME",13,"A/D OR JOYSTICK: PREVIOUS / NEXT",13,"TWO DIGITS: SELECT DIRECTLY",13,"RETURN / FIRE: OPEN",13,13,"INTRO: ANY KEY / FIRE RETURNS HERE",13,"GAME: STARTS A FRESH CHECKPOINT",13,0
sel_end:
