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
 sta sel_user
 lda #$ff
 sta sel_art_loaded
 lda #0
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
 lda sel_mode
 lbeq sel_wait
 lda #<sel_user_text
 ldy #>sel_user_text
 jsr sel_print
 lda sel_user
 clc
 adc #1
 jsr sel_number
 jsr sel_text_font
 jsr sel_art_prepare
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
 cmp #'U'
 lbne sel_digit_input
 lda sel_user
 clc
 adc #1
 and #3
 sta sel_user
 jmp sel_menu
sel_digit_input:
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
 lda sel_user
 sta $02f5
 eor #$ff
 sta $02f6
 jsr native_start
 lda #0
 sta $02f0
 jmp sel_error
sel_preview:
 lda #$ff
 sta sel_art_loaded
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

; KERNAL writes screen codes 1-26 for uppercase letters. The native atlas
; reserves those codes for terrain and keeps text at ASCII 65-90 instead.
sel_text_font:
 lda #0
 sta PTR
 lda #4
 sta PTR+1
 ldy #0
sel_text_cell:
 lda (PTR),y
 cmp #1
 lbcc sel_text_next
 cmp #27
 lbcs sel_text_next
 clc
 adc #64
 sta (PTR),y
sel_text_next:
 inc PTR
 bne sel_text_check
 inc PTR+1
sel_text_check:
 lda PTR+1
 cmp #7
 lbne sel_text_cell
 lda PTR
 cmp #$e8
 lbne sel_text_cell
 rts

; Load the converted island character atlas and sprite bank into the selector.
; The same NGF1/NGP1 streams are consumed by the native game, so selection
; previews exercise the exact graphics that gameplay will use.
sel_art_prepare:
 lda sel_art_loaded
 cmp sel_index
 lbeq sel_art_show
 jsr sel_load_art
 bcs sel_art_done
 jsr sel_load_sprites
 bcs sel_art_done
 lda sel_index
 sta sel_art_loaded
sel_art_show:
 lda #$1e
 sta $d018
 jsr sel_render_art
 lda #$0f
 sta $d015
sel_art_done:
 rts
sel_load_art:
 lda sel_index
 clc
 adc #1
 ldx #$30
sel_art_tens:
 cmp #10
 lbcc sel_art_ones
 sec
 sbc #10
 inx
 lbne sel_art_tens
sel_art_ones:
 stx sel_art_file+4
 clc
 adc #$30
 sta sel_art_file+5
 lda #6
 ldx #<sel_art_file
 ldy #>sel_art_file
 jsr ld_open
 bcs sel_art_fail
 ldx #0
 ldy #0
 jsr ld_read
 bcs sel_art_fail_close
 cmp #'N'
 lbne sel_art_fail_close
 jsr ld_read
 bcs sel_art_fail_close
 cmp #'G'
 lbne sel_art_fail_close
 jsr ld_read
 bcs sel_art_fail_close
 cmp #'F'
 lbne sel_art_fail_close
 jsr ld_read
 bcs sel_art_fail_close
 cmp #'1'
 lbne sel_art_fail_close
 lda #<$3800
 sta PTR
 lda #>$3800
 sta PTR+1
 lda #<$0800
 sta ld_left
 lda #>$0800
 sta ld_left+1
 jsr ld_unpack
 bcs sel_art_fail_close
 lda #<$c000
 sta PTR
 lda #>$c000
 sta PTR+1
 jsr sel_read_144
 bcs sel_art_fail_close
 lda #<$c100
 sta PTR
 lda #>$c100
 sta PTR+1
 jsr sel_read_144
 bcs sel_art_fail_close
 jsr ld_close
 lda #$1e
 sta $d018
 clc
 rts
sel_art_fail_close:
 jsr ld_close
sel_art_fail:
 sec
 rts
sel_read_144:
 ldx #144
sel_read_144_loop:
 stx sel_count
 ldx #0
 ldy #0
 jsr ld_read
 bcs sel_read_144_fail
 ldy #0
 sta (PTR),y
 inc PTR
 bne sel_read_144_next
 inc PTR+1
sel_read_144_next:
 ldx sel_count
 dex
 bne sel_read_144_loop
 clc
 rts
sel_read_144_fail:
 sec
 rts
sel_load_sprites:
 lda sel_index
 ldx #$30
sel_sprite_age:
 cmp #3
 lbcc sel_sprite_age_done
 sec
 sbc #3
 inx
 jmp sel_sprite_age
sel_sprite_age_done:
 stx sel_sprite_file+5
 lda #6
 ldx #<sel_sprite_file
 ldy #>sel_sprite_file
 jsr ld_open
 lbcs sel_sprite_fail
 ldx #0
 ldy #0
 jsr ld_read
 lbcs sel_sprite_fail_close
 cmp #'N'
 lbne sel_sprite_fail_close
 jsr ld_read
 lbcs sel_sprite_fail_close
 cmp #'G'
 lbne sel_sprite_fail_close
 jsr ld_read
 lbcs sel_sprite_fail_close
 cmp #'P'
 lbne sel_sprite_fail_close
 jsr ld_read
 lbcs sel_sprite_fail_close
 cmp #'1'
 lbne sel_sprite_fail_close
 lda #<$3200
 sta PTR
 lda #>$3200
 sta PTR+1
 lda #<$0140
 sta ld_left
 lda #>$0140
 sta ld_left+1
 jsr ld_unpack
 lbcs sel_sprite_fail_close
 jsr ld_close
 lda #$c8
 sta $07f8
 clc
 adc #1
 sta $07f9
 clc
 adc #1
 sta $07fa
 clc
 adc #1
 sta $07fb
 lda #$0f
 sta $d015
 lda #0
 sta $d010
 sta $d017
 sta $d01d
 lda #$0f
 sta $d01c
 lda #0
 sta $d025
 lda #15
 sta $d026
 ldx #0
 lda #60
sel_sprite_position:
 sta $d000,x
 clc
 adc #48
 inx
 pha
 lda #190
 sta $d000,x
 pla
 inx
 cpx #8
 lbne sel_sprite_position
 lda #1
 sta $d027
 sta $d028
 lda #2
 sta $d029
 sta $d02a
 clc
 rts
sel_sprite_fail_close:
 jsr ld_close
sel_sprite_fail:
 sec
 rts
sel_render_art:
 ; Show all 144 converted map glyphs in a compact gallery while the four
 ; selected sprite frames remain visible. This uses the complete NART table.
 lda #<$0700
 sta PTR
 lda #>$0700
 sta PTR+1
 lda #<$c000
 sta CPTR
 lda #>$c000
 sta CPTR+1
 lda #0
 sta sel_count
sel_gallery_loop:
 ldy #0
 lda (CPTR),y
 sta (PTR),y
 ldx sel_count
 lda $c100,x
 sta $db00,x
 inc PTR
 bne sel_gallery_ptr
 inc PTR+1
sel_gallery_ptr:
 inc CPTR
 bne sel_gallery_map
 inc CPTR+1
sel_gallery_map:
 inc sel_count
 lda sel_count
 cmp #144
 lbne sel_gallery_loop
 rts
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
sel_user: !byte 0
sel_art_loaded: !byte $ff
sel_tens: !byte $ff
sel_joy: !byte $ff
sel_count: !byte 0
sel_bases: !fill 29,0
sel_title: !text "MEGA-LO-MANIA 64",13,"SCENE / ISLAND SELECTOR",13,13,0
sel_intro_text: !text "INTRO PREVIEW 01-29: ",0
sel_game_text: !text "GAME ISLAND 01-28: ",0
sel_art_file: !text "NART00",0
sel_sprite_file: !text "NSPR00",0
sel_user_text: !text 13,"U CHANGE USER: ",0
sel_controls: !text 13,13,"I INTRO   G GAME   U USER",13,"A/D OR JOYSTICK: PREVIOUS / NEXT",13,"TWO DIGITS: SELECT DIRECTLY",13,"RETURN / FIRE: OPEN",13,13,"INTRO: ANY KEY / FIRE RETURNS HERE",13,"GAME: STARTS A FRESH CHECKPOINT",13,0
sel_end:
