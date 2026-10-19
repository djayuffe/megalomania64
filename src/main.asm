; MEGA-LO-MANIA 64  —  original fan-inspired C64C real-time strategy game
; 6510/8500 CPU, PAL+NTSC VIC-II. Program $1000, sprite $3700, charset $3800.
; Python build: python tools/build.py
; No BASIC runtime dependence; GETIN uses standard KERNAL IRQ keyboard scanning.
; Original 28-island campaign data, 10 progressive technology epochs, port 2 joystick.

SCR = $0400
COL = $D800
JOYP = $DC00
RASTER = $D012
SID_GATE = $D404
KGETIN = $FFE4
PTR = $FB
CPTR = $FD
SAVE_BUFFER = $C000          ; 256-byte scratch buffer in free RAM
TRUCE_TICKS = 90             ; length of an agreed truce, in strategy ticks
TRUCE_COOL = 60              ; cool-down before a faction talks again

* = $0801
!byte $0B,$08,$0A,$00,$9E,$34,$30,$39,$36,$00,$00,$00   ; 10 SYS4096

* = $1000
start:
 sei
 cld
 lda $dd00
 and #$fc
 ora #$03
 sta $dd00                   ; VIC bank 0
 lda #$1b
 sta $d011                   ; text, 25 lines
 lda #$18
 sta $d016                   ; mixed MC/hires chars
 lda #$1e
 sta $d018                   ; screen $0400, chars $3800
 lda #$06
 sta $d020
 sta $d021
 lda #$05
 sta $d022
 lda #$0d
 sta $d023
 lda #$0f
 sta $d418
 lda #$09
 sta $d405
 lda #$a5
 sta $d406
 lda #$08
 sta $d40c
 sta $d413
 lda #$a6
 sta $d40d
 sta $d414
 lda #$11
 sta $d40b
 lda #$21
 sta $d412
 jsr set_speed                ; frames per tick from speed setting + PAL/NTSC
 lda #$00
 sta SID_GATE
 lda #$03
 sta $d015                   ; sprite 0 = cursor, sprite 1 = army-source marker
 lda #$07
 sta $d027
 lda #$0a
 sta $d028
 lda #$dc
 sta $07f8                   ; cursor sprite at $3700
 lda #$dd
 sta $07f9                   ; source marker sprite at $3740
 jsr orig_init                ; sprites 2/3: original-art army + building icon
 lda #1
 sta $cc                     ; KERNAL cursor blink off: it XORs screen RAM otherwise
 lda #0
 sta $9d                     ; KERNAL messages off (no "SAVING"/"SEARCHING" over the map)
 jsr irq_install             ; raster IRQ engine (ends with CLI)
 jsr title_screen
 jsr new_game
 lda vblank
 sta lastvb
main_loop:
 jsr wait_frame              ; sleeps until the raster IRQ bumps vblank
 lda vblank
 sec
 sbc lastvb
 sta elapsed
 lda vblank
 sta lastvb
 jsr read_keys
 lda state
 bne main_loop              ; 1 paused, 2+ game over
 lda elapsed
 cmp #9
 bcc elapsed_ok
 lda #8                     ; clamp after long disk I/O
elapsed_ok:
 clc
 adc frames
 sta frames
 cmp frames_per_tick
 bcc main_loop
 sec
 sbc frames_per_tick        ; keep remainder: drift-free tick clock
 sta frames
 jsr simulate
 jmp main_loop

new_game:
 lda #0
 sta campaign_island
 lda #12
 sta reserve
 jsr load_island
 rts

; 28 unique game maps; island 0..26 in 9 three-island epochs, final island 27.
; Each stage reads original deterministic per-island terrain/mineral tables.
load_island:
 jsr orig_init
 lda #0
 sta frames
 sta ticks
 sta state
 sta load_mode
 sta soundtime
 sta music_over
 sta fx_timer
 sta shake_timer
 sta selected
 sta source
 sta music_frame
 sta music_pos
 sta heavy
 lda #31
 sta joylast
 lda #$20
 sta SID_GATE
 ldy campaign_island
 lda epoch_by_island,y
 sta epoch
 jsr set_border
 lda world_terrain_lo,y
 sta PTR
 lda world_terrain_hi,y
 sta PTR+1
 ldx #11
terrain_init:
 txa
 tay
 lda (PTR),y
 sta terrain,x
 dex
 bpl terrain_init
 ldy campaign_island
 lda world_vein_lo,y
 sta PTR
 lda world_vein_hi,y
 sta PTR+1
 ldx #11
resource_init:
 txa
 tay
 lda (PTR),y
 sta vein,x
 lda #0
 sta owner,x
 sta people,x
 sta ore,x
 sta miners,x
 sta labs,x
 sta weapons,x
 sta fort,x
 sta level,x
 sta research,x
 sta buildings,x
 sta minegrade,x
 sta policy,x
 sta doctrine,x
 dex
 bpl resource_init
 ldx #4
truce_reset:
 lda #0
 sta truce,x
 sta truce_cool,x
 dex
 bpl truce_reset
 ldy campaign_island
 ldx spawn_human,y
 stx selected
 stx source
 lda #1
 sta owner,x
 lda reserve
 lsr
 lsr
 clc
 adc #22
 sta people,x
 lda #16
 sta ore,x
 lda #2
 sta miners,x
 sta labs,x
 lda #6
 sta weapons,x
 lda #1
 sta fort,x
 sta minegrade,x
 lda #7
 sta buildings,x
 lda epoch
 lsr
 sta level,x
 ; Three computer generals, each with independent ownership and economy.
 ldy campaign_island
 ldx spawn_cpu,y
 lda #2
 jsr setup_enemy
 ldy campaign_island
 ldx spawn_rival3,y
 lda #3
 jsr setup_enemy
 ldy campaign_island
 ldx spawn_rival4,y
 lda #4
 jsr setup_enemy
 ldy epoch
 lda sea_palette,y
 sta $d022
 lda earth_palette,y
 sta $d023
 lda #0
 sta ai_cursor
 lda #2
 sta ai_faction
 jsr clear_screen
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
 rts

; A holds owner 2..4, X holds distinct starting sector.
setup_enemy:
 sta owner,x
 lda epoch
 asl
 clc
 adc #19
 sta people,x
 lda #14
 sta ore,x
 lda #2
 sta miners,x
 lda #1
 sta labs,x
 sta fort,x
 sta minegrade,x
 lda #4
 sta weapons,x
 lda #7
 sta buildings,x
 lda epoch
 lsr
 sta level,x
 lda owner,x
 sec
 sbc #2
 sta doctrine,x              ; red=industry, blue=military, gold=defense
 rts

next_island:
 lda state
 cmp #2
 bne next_return
 lda campaign_island
 cmp #27
 beq next_return
 inc campaign_island
 lda reserve
 clc
 adc #6
 cmp #91
 bcc next_keep
 lda #90
next_keep:
 sta reserve
 jsr load_island
next_return:
 rts

; $fb/$fc points to zero-terminated byte-coded text. Plot uses $fd/$fe only.
print_text:
 lda #0
 sta text_index
text_loop:
 ldy text_index
 lda (PTR),y
 beq text_done
 ldx text_x
 ldy text_y
 jsr plot
 inc text_x
 inc text_index
 bne text_loop
text_done:
 rts

; A=glyph X=col Y=row ink=color; all screen writes bounded by callers.
plot:
 sta glyph
 lda row_lo,y
 sta CPTR
 lda row_hi,y
 sta CPTR+1
 txa
 tay
 lda glyph
 sta (CPTR),y
 lda CPTR+1
 clc
 adc #$d4                   ; $0400 -> $d800
 sta CPTR+1
 lda ink
 sta (CPTR),y
 rts

; print 00..99 at x,y held in text_x,text_y (advances x twice)
print2:
 lda value
 sta remainder
 lda #0
 sta tens
p2_loop:
 lda remainder
 cmp #10
 bcc p2_digits
 sec
 sbc #10
 sta remainder
 inc tens
 jmp p2_loop
p2_digits:
 lda tens
 clc
 adc #'0'
 ldx text_x
 ldy text_y
 jsr plot
 inc text_x
 lda remainder
 clc
 adc #'0'
 ldx text_x
 ldy text_y
 jsr plot
 inc text_x
 rts

; Copy 1024 bytes screen + color in 4 stripes.
clear_screen:
 ldx #0
cl_loop:
 lda #32
 sta $0400,x
 sta $0500,x
 sta $0600,x
 sta $0700,x
 lda #1
 sta $d800,x
 sta $d900,x
 sta $da00,x
 sta $db00,x
 inx
 bne cl_loop
 lda #$dc
 sta $07f8
 lda #$dd
 sta $07f9
 rts

; fixed titles and controls
; Helper setup coordinates precede setting PTR for print_text.
draw_static:
 ; Procedural sea tiles in unused map cells (not a 320x200 bitmap wipe).
 ; A single static pass on each island load; terrain tiles replace water cells.
 lda #14
 sta ink
 lda #3
 sta dy
sea_row:
 lda #0
 sta dx
sea_col:
 ldx dx
 ldy dy
 lda #6
 jsr plot
 inc dx
 lda dx
 cmp #29
 bne sea_col
 inc dy
 lda dy
 cmp #21
 bne sea_row
 lda #1
 sta ink
 lda #0
 sta text_x
 sta text_y
 lda #<title_msg
 sta PTR
 lda #>title_msg
 sta PTR+1
 jsr print_text
 jsr print_island_name         ; original island name (ALOHA, BAZOOKA, ... ZAPPA)
 lda #22
 sta text_y
 lda #0
 sta text_x
 lda #<help_a
 sta PTR
 lda #>help_a
 sta PTR+1
 jsr print_text
 lda #23
 sta text_y
 lda #0
 sta text_x
 lda #<help_b
 sta PTR
 lda #>help_b
 sta PTR+1
 jsr print_text
 lda #24
 sta text_y
 lda #0
 sta text_x
 lda #<help_c
 sta PTR
 lda #>help_c
 sta PTR+1
 jsr print_text
 rts

; render every sector once on new game, and incrementally thereafter
draw_all:
 lda #0
 sta sid
all_loop:
 jsr draw_sector
 inc sid
 lda sid
 cmp #12
 bne all_loop
 rts

; sector uses 6x5-character tiles with 1-character sea lanes; each is 48x40px
draw_sector:
 ldx sid
 lda sector_x,x
 sta basex
 lda sector_y,x
 sta basey
 lda terrain,x
 sta tilechar
 lda sid
 eor campaign_island
 and #3
 tax
 lda coast_mask_lo,x
 sta PTR
 lda coast_mask_hi,x
 sta PTR+1
 ldx sid
 lda owner,x
 beq sector_free
 cmp #1
 beq sector_you
 cmp #2
 beq sector_red
 cmp #3
 beq sector_blue
 lda #$09                    ; faction 4 brown
 bne sector_color
sector_blue:
 lda #$0e                    ; faction 3 pale blue
 bne sector_color
sector_red:
 lda #$0a                    ; faction 2 red
 bne sector_color
sector_you:
 lda #$0d                    ; multicolor green
 bne sector_color
sector_free:
 lda #$0b                    ; multicolor cyan
sector_color:
 sta ink
 sta territory_ink
 lda #0
 sta dy
sector_row:
 lda #0
 sta dx
sector_col:
 ; Coastline mask: irregular silhouettes with interleaved open water.
 ; The map stays in character mode; no bitmap refresh or large buffers.
 lda dy
 asl
 clc
 adc dy
 asl
 clc
 adc dx
 tay
 lda (PTR),y
 bne sector_land_cell
 lda #14
 sta ink
 lda #6
 jmp sector_render_tile
sector_land_cell:
 lda territory_ink
 sta ink
 ; deterministic biome detail: only one variant tile per four map cells
 lda dx
 eor dy
 and #3
 bne sector_plain_tile
 lda tilechar
 clc
 adc #11                 ; tile 1..5 -> alternate 12..16
 bne sector_render_tile
sector_plain_tile:
 lda tilechar
sector_render_tile:
 pha
 lda basex
 clc
 adc dx
 tax
 lda basey
 clc
 adc dy
 tay
 pla
 jsr plot
 inc dx
 lda dx
 cmp #6
 bne sector_col
 inc dy
 lda dy
 cmp #5
 bne sector_row
 ; Restore ownership ink following ocean cells.
 lda territory_ink
 sta ink
 ; Epoch-specific citadel silhouette and variation in natural geography.
 ldx sid
 lda owner,x
 beq sector_nohq
 lda epoch
 lsr
 clc
 adc #17                    ; 17..21 era-specific tower shapes
 bne sector_icon
sector_nohq:
 lda #3
sector_icon:
 ldx basex
 inx
 inx
 ldy basey
 iny
 jsr plot
 ; Builder icons: mine, laboratory, factory (up to three 8x8 glyphs).
 ldx sid
 lda buildings,x
 and #1
 beq sector_lab_icon
 lda #22
 ldx basex
 inx
 ldy basey
 clc
 adc #0
 jsr plot
sector_lab_icon:
 ldx sid
 lda buildings,x
 and #2
 beq sector_factory_icon
 lda #23
 ldx basex
 inx
 inx
 ldy basey
 jsr plot
sector_factory_icon:
 ldx sid
 lda buildings,x
 and #4
 beq sector_population
 lda #24
 ldx basex
 inx
 inx
 inx
 ldy basey
 jsr plot
sector_population:
 ; population bottom-centre printed in high-resolution white
 lda #1
 sta ink
 ldx sid
 lda people,x
 sta value
 lda basex
 clc
 adc #2
 sta text_x
 lda basey
 clc
 adc #3
 sta text_y
 jsr print2
 rts

draw_cursor:
 ldx selected
 lda sector_x,x
 asl
 asl
 asl
 clc
 adc #32
 sta $d000
 lda sector_y,x
 asl
 asl
 asl
 clc
 adc #58
 sta $d001
 rts

; W/A/S/D moves selection. RETURN sets sending sector.
read_keys:
 jsr KGETIN
 sta keycode
 bne key_available
 jsr read_joystick
 sta keycode
 lbeq no_key
key_available:
 lda load_mode
 beq key_normal
 jsr parse_stage_code
 rts
key_normal:
 lda keycode
 cmp #'L'
 bne not_load_stage
 lda #1
 sta load_mode
 lda #<msg_stage
 sta PTR
 lda #>msg_stage
 sta PTR+1
 jsr message
 rts
not_load_stage:
 lda keycode
 cmp #'C'
 bne not_continue
 jsr next_island
 rts
not_continue:
 cmp #'N'
 bne not_restart
 jsr new_game
 rts
not_restart:
 cmp #'O'
 bne not_save
 jsr save_game
 rts
not_save:
 cmp #'I'
 bne not_restore
 jsr restore_game
 rts
not_restore:
 cmp #32
 bne not_pause
 lda state
 cmp #2
 lbcs no_key
 eor #1
 sta state
 beq unpaused
 lda #<msg_pause
 sta PTR
 lda #>msg_pause
 sta PTR+1
 jsr message
 rts
unpaused:
 lda #<msg_go
 sta PTR
 lda #>msg_go
 sta PTR+1
 jsr message
 rts
not_pause:
 lda state
 lbne no_key
 lda keycode
 cmp #'W'
 bne key_a
 lda selected
 cmp #4
 lbcc key_invalid
 sec
 sbc #4
 sta selected
 jmp moved
key_a:
 cmp #'A'
 bne key_s
 ldx selected
 lda grid_col,x
 lbeq key_invalid
 dec selected
 jmp moved
key_s:
 cmp #'S'
 bne key_d
 lda selected
 cmp #8
 lbcs key_invalid
 clc
 adc #4
 sta selected
 jmp moved
key_d:
 cmp #'D'
 bne key_enter
 ldx selected
 lda grid_col,x
 cmp #3
 lbeq key_invalid
 inc selected
 jmp moved
key_enter:
 cmp #13
 bne key_b
 ldx selected
 lda owner,x
 cmp #1
 lbne key_invalid
 lda selected
 sta source
 lda #<msg_source
 sta PTR
 lda #>msg_source
 sta PTR+1
 jsr message
 jsr beep_ok
 jmp draw_panel
key_b:
 cmp #'B'
 bne key_v
 jsr upgrade_mine
 jmp draw_panel
key_v:
 cmp #'V'
 bne key_g
 jsr build_lab
 jmp draw_panel
key_g:
 cmp #'G'
 bne key_m
 jsr build_factory
 jmp draw_panel
key_m:
 cmp #'M'
 bne key_r
 jsr add_miner
 jmp draw_panel
key_r:
 cmp #'R'
 bne key_j
 jsr add_lab
 jmp draw_panel
key_j:
 cmp #'J'
 bne key_k
 ldx selected
 lda owner,x
 cmp #1
 lbne key_invalid
 lda miners,x
 lbeq key_invalid
 dec miners,x
 jmp draw_panel
key_k:
 cmp #'K'
 bne key_p
 ldx selected
 lda owner,x
 cmp #1
 lbne key_invalid
 lda labs,x
 lbeq key_invalid
 dec labs,x
 jmp draw_panel
key_p:
 cmp #'P'
 bne key_f
 jsr make_weapon
 jmp draw_panel
key_f:
 cmp #'F'
 bne key_x
 jsr make_fort
 jmp draw_panel
key_x:
 cmp #'Q'
 bne key_transport
 jsr cycle_doctrine
 jmp draw_panel
key_transport:
 cmp #'H'
 bne key_autoarms
 jsr reinforce
 jmp draw_panel
key_autoarms:
 cmp #'Y'
 bne key_autofort
 lda #1
 jsr toggle_policy
 jmp draw_panel
key_autofort:
 cmp #'Z'
 bne key_x_attack
 lda #2
 jsr toggle_policy
 jmp draw_panel
key_x_attack:
 cmp #'T'
 bne key_standard_attack
 lda #1
 sta heavy
 jsr player_attack
 lda #0
 sta heavy
 jmp draw_panel
key_standard_attack:
 cmp #'X'
 lbne key_extra
 lda #0
 sta heavy
 jsr player_attack
 jmp draw_panel
moved:
 jsr draw_cursor
 lda #SFX_TICK
 jsr sfx_play
 jmp draw_panel
key_invalid:
 jsr beep_no
no_key:
 rts

; Optional stage-select code. Two decimal digits 01..28 load a checkpoint
; (not a complete live-game save: the current island economy resets).
parse_stage_code:
 lda keycode
 cmp #'N'
 lbeq stage_cancel
 cmp #'0'
 lbcc stage_invalid
 cmp #':'
 lbcs stage_invalid
 sec
 sbc #'0'
 pha
 lda load_mode
 cmp #1
 bne stage_second
 pla
 cmp #3
 lbcs stage_invalid
 sta load_tens
 lda #2
 sta load_mode
 lda #<msg_stage_two
 sta PTR
 lda #>msg_stage_two
 sta PTR+1
 jsr message
 rts
stage_second:
 pla
 sta load_ones
 ldx load_tens
 lda load_ones
 beq stage_accum_start
stage_accum_start:
 cpx #0
 beq stage_validate
 clc
stage_accum:
 adc #10
 dex
 bne stage_accum
stage_validate:
 cmp #1
 lbcc stage_invalid
 cmp #29
 lbcs stage_invalid
 sec
 sbc #1
 sta campaign_island
 lda #12
 sta reserve
 ldx campaign_island
 beq stage_start
stage_reserve:
 lda reserve
 cmp #90
 bcs stage_start
 clc
 adc #6
 cmp #91
 bcc stage_store_reserve
 lda #90
stage_store_reserve:
 sta reserve
 dex
 bne stage_reserve
stage_start:
 jsr load_island
 rts
stage_cancel:
 lda #0
 sta load_mode
 lda #<msg_go
 sta PTR
 lda #>msg_go
 sta PTR+1
 jsr message
 rts
stage_invalid:
 lda #0
 sta load_mode
 lda #<msg_stage_error
 sta PTR
 lda #>msg_stage_error
 sta PTR+1
 jsr message
 jsr beep_no
 rts

; Port 2 joystick (sampled by the raster IRQ into joy_raw) is decoded by
; read_joystick in joystick.asm: directions move, FIRE sets base/raids, FIRE+direction chords.

; only add workers if at least 3 idle population remain; max 12 per job.
can_assign:
 ldx selected
 lda owner,x
 cmp #1
 bne cant_assign
 lda miners,x
 clc
 adc labs,x
 clc
 adc #3
 cmp people,x
 bcs cant_assign
 sec
 rts
cant_assign:
 clc
 rts
add_miner:
 jsr can_assign
 bcc denied
 ldx selected
 lda miners,x
 cmp #12
 bcs denied
 inc miners,x
 jsr beep_ok
 rts
add_lab:
 jsr can_assign
 bcc denied
 ldx selected
 lda buildings,x
 and #2
 beq denied
 lda labs,x
 cmp #12
 bcs denied
 inc labs,x
 jsr beep_ok
 rts
denied:
 lda #<msg_denied
 sta PTR
 lda #>msg_denied
 sta PTR+1
 jsr message
 jsr beep_no
 rts
 ; Building tech chain: colony starts with a primitive mine. Mines can be
; upgraded twice, labs unlock research, factories unlock weapon production.
upgrade_mine:
 ldx selected
 lda owner,x
 cmp #1
 lbne denied
 lda minegrade,x
 cmp #2
 lbcs denied
 lda ore,x
 cmp #8
 lbcc denied
 sec
 sbc #8
 sta ore,x
 inc minegrade,x
 lda selected
 sta sid
 jsr draw_sector
 jmp beep_ok
build_lab:
 ldx selected
 lda owner,x
 cmp #1
 lbne denied
 lda buildings,x
 and #2
 lbne denied
 lda ore,x
 cmp #6
 lbcc denied
 sec
 sbc #6
 sta ore,x
 lda buildings,x
 ora #2
 sta buildings,x
 lda selected
 sta sid
 jsr draw_sector
 jmp beep_ok
build_factory:
 ldx selected
 lda owner,x
 cmp #1
 lbne denied
 lda buildings,x
 and #4
 lbne denied
 lda ore,x
 cmp #10
 lbcc denied
 sec
 sbc #10
 sta ore,x
 lda buildings,x
 ora #4
 sta buildings,x
 lda selected
 sta sid
 jsr draw_sector
 jmp beep_ok

; Per-sector automation: Y auto manufacture, Z auto fortify.
; No opponent sector may be modified from the keyboard.
cycle_doctrine:
 ldx selected
 lda owner,x
 cmp #1
 lbne denied
 inc doctrine,x
 lda doctrine,x
 cmp #3
 bcc doctrine_done
 lda #0
 sta doctrine,x
doctrine_done:
 jsr beep_ok
 rts

toggle_policy:
 sta mask
 ldx selected
 lda owner,x
 cmp #1
 lbne denied
 lda policy,x
 eor mask
 sta policy,x
 jsr beep_ok
 rts

; Friendly sector reinforcement does not destroy buildings, deposits, or jobs.
; Transfer half of sender population, capped at 90 on receiver; move up to
; four weapons along with the troops. Ownership and both regions are checked.
reinforce:
 ldx source
 lda owner,x
 cmp #1
 lbne attack_unavailable
 jsr adjacent
 lbcc attack_unavailable
 ldx selected
 lda owner,x
 cmp #1
 lbne attack_unavailable
 lda people,x
 cmp #90
 lbcs denied
 ldx source
 lda people,x
 cmp #8
 lbcc attack_too_small
 lsr
 sta force
 ldx selected
 lda #90
 sec
 sbc people,x
 cmp force
 bcs reinforce_can_send
 sta force
reinforce_can_send:
 lda people,x
 clc
 adc force
 sta people,x
 ldx source
 lda people,x
 sec
 sbc force
 sta people,x
 ; Move four weapons at most, without overflowing target storage.
 lda weapons,x
 cmp #4
 bcc reinforce_arms
 lda #4
reinforce_arms:
 sta usedarms
 ldx selected
 lda weapons,x
 clc
 adc usedarms
 cmp #91
 bcc reinforce_store_arms
 lda #90
 sec
 sbc weapons,x
 sta usedarms
 lda #90
reinforce_store_arms:
 sta weapons,x
 ldx source
 lda weapons,x
 sec
 sbc usedarms
 sta weapons,x
 lda source
 sta sid
 jsr draw_sector
 lda selected
 sta sid
 jsr draw_sector
 lda #<msg_reinforce
 sta PTR
 lda #>msg_reinforce
 sta PTR+1
 jsr message
 jsr beep_ok
 rts

make_weapon:
 ldx selected
 lda owner,x
 cmp #1
 lbne denied
 lda buildings,x
 and #4
 lbeq denied
 lda ore,x
 cmp #4
 lbcc denied
 lda weapons,x
 cmp #90
 lbcs denied
 sec
 lda ore,x
 sbc #4
 sta ore,x
 inc weapons,x
 jsr beep_ok
 rts
make_fort:
 ldx selected
 lda owner,x
 cmp #1
 lbne denied
 lda ore,x
 cmp #12
 lbcc denied
 lda fort,x
 cmp #9
 lbcs denied
 sec
 lda ore,x
 sbc #12
 sta ore,x
 inc fort,x
 jsr beep_ok
 rts

; temporary status message on line 2; PTR must address string.
message:
 lda #1
 sta ink
 lda #2
 sta text_y
 lda #0
 sta text_x
msg_clear:
 ldx text_x
 ldy text_y
 lda #32
 jsr plot
 inc text_x
 lda text_x
 cmp #40
 bne msg_clear
 lda #0
 sta text_x
 jsr print_text
 rts

; populate text/stat sidebar, sector attributes, and source target indicator.
draw_panel:
 lda #1
 sta ink
 lda #3
 sta dy
panel_row:
 lda #30
 sta dx
panel_col:
 ldx dx
 ldy dy
 lda #32
 jsr plot
 inc dx
 lda dx
 cmp #40
 bne panel_col
 inc dy
 lda dy
 cmp #21
 bne panel_row
 lda #30
 sta text_x
 lda #3
 sta text_y
 lda #<hud_sector
 sta PTR
 lda #>hud_sector
 sta PTR+1
 jsr print_text
 lda #30
 sta text_x
 lda #5
 sta text_y
 lda #<hud_owner
 sta PTR
 lda #>hud_owner
 sta PTR+1
 jsr print_text
 lda #30
 sta text_x
 lda #7
 sta text_y
 lda #<hud_pop
 sta PTR
 lda #>hud_pop
 sta PTR+1
 jsr print_text
 lda #30
 sta text_x
 lda #9
 sta text_y
 lda #<hud_ore
 sta PTR
 lda #>hud_ore
 sta PTR+1
 jsr print_text
 lda #30
 sta text_x
 lda #11
 sta text_y
 lda #<hud_vein
 sta PTR
 lda #>hud_vein
 sta PTR+1
 jsr print_text
 lda #30
 sta text_x
 lda #13
 sta text_y
 lda #<hud_tech
 sta PTR
 lda #>hud_tech
 sta PTR+1
 jsr print_text
 ; Epoch vocabulary on the free line between tech and miners.
 ldx epoch
 lda epoch_title_lo,x
 sta PTR
 lda epoch_title_hi,x
 sta PTR+1
 lda #30
 sta text_x
 lda #14
 sta text_y
 jsr print_text
 lda #30
 sta text_x
 lda #15
 sta text_y
 lda #<hud_mine
 sta PTR
 lda #>hud_mine
 sta PTR+1
 jsr print_text
 lda #30
 sta text_x
 lda #17
 sta text_y
 lda #<hud_lab
 sta PTR
 lda #>hud_lab
 sta PTR+1
 jsr print_text
 lda #30
 sta text_x
 lda #19
 sta text_y
 lda #<hud_arms
 sta PTR
 lda #>hud_arms
 sta PTR+1
 jsr print_text
 ; Values in second line after each attribute
panel_values:
 ldx selected
 txa
 clc
 adc #1
 sta value
 lda #37
 sta text_x
 lda #3
 sta text_y
 jsr print2
 ldx selected
 lda owner,x
 cmp #1
 beq own_player
 cmp #2
 beq own_cpu
 cmp #3
 beq own_rival3
 cmp #4
 beq own_rival4
 lda #<hud_free
 sta PTR
 lda #>hud_free
 sta PTR+1
 jmp own_show
own_player:
 lda #<hud_you
 sta PTR
 lda #>hud_you
 sta PTR+1
 jmp own_show
own_cpu:
 lda #<hud_cpu
 sta PTR
 lda #>hud_cpu
 sta PTR+1
 jmp own_show
own_rival3:
 lda #<hud_rival3
 sta PTR
 lda #>hud_rival3
 sta PTR+1
 jmp own_show
own_rival4:
 lda #<hud_rival4
 sta PTR
 lda #>hud_rival4
 sta PTR+1
own_show:
 lda #36
 sta text_x
 lda #5
 sta text_y
 jsr print_text
 ldx selected
 lda people,x
 sta value
 lda #37
 sta text_x
 lda #7
 sta text_y
 jsr print2
 ldx selected
 lda ore,x
 sta value
 lda #37
 sta text_x
 lda #9
 sta text_y
 jsr print2
 ldx selected
 lda vein,x
 sta value
 lda #37
 sta text_x
 lda #11
 sta text_y
 jsr print2
 ldx selected
 lda level,x
 sta value
 lda #37
 sta text_x
 lda #13
 sta text_y
 jsr print2
 ldx selected
 lda miners,x
 sta value
 lda #37
 sta text_x
 lda #15
 sta text_y
 jsr print2
 ldx selected
 lda labs,x
 sta value
 lda #37
 sta text_x
 lda #17
 sta text_y
 jsr print2
 ldx selected
 lda weapons,x
 sta value
 lda #37
 sta text_x
 lda #19
 sta text_y
 jsr print2
 ; Active automation policy between worker and weapon rows.
 lda #30
 sta text_x
 lda #18
 sta text_y
 lda #<hud_auto
 sta PTR
 lda #>hud_auto
 sta PTR+1
 jsr print_text
 ldx selected
 lda policy,x
 and #1
 clc
 adc #'0'
 ldx #35
 ldy #18
 jsr plot
 ldx selected
 lda policy,x
 and #2
 lsr
 clc
 adc #'0'
 ldx #37
 ldy #18
 jsr plot
 ; Selected research doctrine: I industry, M military, D defense.
 lda #30
 sta text_x
 lda #16
 sta text_y
 lda #<hud_doctrine
 sta PTR
 lda #>hud_doctrine
 sta PTR+1
 jsr print_text
 ldx selected
 ldy doctrine,x
 lda doctrine_char,y
 ldx #39
 ldy #16
 jsr plot
 ; One compact 3-bit construction indicator on row 20.
 lda #30
 sta text_x
 lda #20
 sta text_y
 lda #<hud_build
 sta PTR
 lda #>hud_build
 sta PTR+1
 jsr print_text
 ldx selected
 lda buildings,x
 and #1
 clc
 adc #'0'
 ldx #34
 ldy #20
 jsr plot
 ldx selected
 lda buildings,x
 and #2
 lsr
 clc
 adc #'0'
 ldx #36
 ldy #20
 jsr plot
 ldx selected
 lda buildings,x
 and #4
 lsr
 lsr
 clc
 adc #'0'
 ldx #38
 ldy #20
 jsr plot
 ; put source and fort row 21, without exceeding screen width
 lda #1
 sta ink
 lda #30
 sta text_x
 lda #21
 sta text_y
 lda #<hud_base
 sta PTR
 lda #>hud_base
 sta PTR+1
 jsr print_text
 ldx source
 txa
 clc
 adc #1
 sta value
 lda #35
 sta text_x
 lda #21
 sta text_y
 jsr print2
 ldx selected
 lda fort,x
 sta value
 lda #38
 sta text_x
 lda #21
 sta text_y
 jsr print2
 jmp panel_extra             ; truce row, weapon name, source marker sprite

; Count territory ownership for HUD and victory/defeat logic.
draw_score:
 jsr draw_speed
 lda #0
 sta you_count
 sta cpu_count
 ldx #11
count_loop:
 lda owner,x
 cmp #1
 bne not_you_count
 inc you_count
not_you_count:
 cmp #2
 bcc not_cpu_count
 inc cpu_count
not_cpu_count:
 dex
 bpl count_loop
 lda #1
 sta ink
 lda #0
 sta text_x
 lda #1
 sta text_y
 lda #<score_msg
 sta PTR
 lda #>score_msg
 sta PTR+1
 jsr print_text
 lda you_count
 sta value
 lda #9
 sta text_x
 lda #1
 sta text_y
 jsr print2
 lda cpu_count
 sta value
 lda #16
 sta text_x
 lda #1
 sta text_y
 jsr print2
 lda ticks
 sta value
 lda #26
 sta text_x
 lda #1
 sta text_y
 jsr print2
 lda #1
 sta ink
 lda #30
 sta text_x
 lda #1
 sta text_y
 lda #<epoch_msg
 sta PTR
 lda #>epoch_msg
 sta PTR+1
 jsr print_text
 lda epoch
 clc
 adc #1
 sta value
 lda #31
 sta text_x
 lda #1
 sta text_y
 jsr print2
 lda campaign_island
 clc
 adc #1
 sta value
 lda #36
 sta text_x
 lda #1
 sta text_y
 jsr print2
 jsr colorize_ui
 lda you_count
 beq game_lost
 cmp #12
 beq game_won
 rts
win_fanfare:
 lda music_over
 cmp #4
 beq wf_done
 lda #4
 sta music_over              ; victory tune
 lda #0
 sta music_pos
 lda #SFX_WIN
 jsr sfx_play
 lda #13
 ldx #50
 jsr fx_flash
wf_done:
 rts
game_lost:
 lda state
 cmp #3
 beq gl_set
 lda #5
 sta music_over              ; defeat tune
 lda #0
 sta music_pos
 lda #SFX_LOSE
 jsr sfx_play
 lda #2
 ldx #40
 jsr fx_flash
gl_set:
 lda #3
 sta state
 lda #<msg_loss
 sta PTR
 lda #>msg_loss
 sta PTR+1
 jsr message
 rts
game_won:
 jsr win_fanfare
 lda campaign_island
 cmp #27
 beq game_final_won
 lda #2
 sta state
 lda #<msg_win
 sta PTR
 lda #>msg_win
 sta PTR+1
 jsr message
 rts
game_final_won:
 lda #4
 sta state
 lda #<msg_campaign_won
 sta PTR
 lda #>msg_campaign_won
 sta PTR+1
 jsr message
 rts

; One strategic tick per 16 video frames (~3.1 Hz PAL, 3.75 Hz NTSC).
simulate:
 inc ticks
 lda ticks
 cmp #100
 bne ticks_ok
 lda #0
 sta ticks
ticks_ok:
 lda ticks
 and #7
 sta growphase
 ldx #0
sim_loop:
 stx simidx
 lda #0
 sta changed
 lda owner,x
 lbeq sim_next
 ; safeguard starving colonies: free workers to maintain >=4 idle citizens.
 ; An undersized garrison must not become permanently unable to breed.
sim_balance:
 lda miners,x
 clc
 adc labs,x
 clc
 adc #4
 cmp people,x
 bcc sim_growth
 beq sim_growth
 lda labs,x
 beq sim_less_miners
 dec labs,x
 jmp sim_balance
sim_less_miners:
 lda miners,x
 beq sim_growth
 dec miners,x
 jmp sim_balance
sim_growth:
 ; idle population reproduces once every 8 ticks, up to 90 population
 lda growphase
 bne sim_mining
 lda people,x
 cmp #90
 bcs sim_mining
 cmp #4
 bcc sim_grow                ; revive injured garrisons of 1..3 citizens
 lda miners,x
 clc
 adc labs,x
 clc
 adc #4
 cmp people,x
 beq sim_grow
 bcs sim_mining
sim_grow:
 inc people,x
 lda #1
 sta changed
sim_mining:
 lda buildings,x
 and #1
 beq sim_research
 lda miners,x
 beq sim_research
 clc
 adc minegrade,x
 sta workleft
 lda doctrine,x
 bne mine_loop_start
 lda level,x
 cmp #2
 bcc mine_loop_start
 inc workleft
 inc workleft
mine_loop_start:
mine_loop:
 lda vein,x
 beq sim_research
 lda ore,x
 cmp #95
 bcs sim_research
 inc ore,x
 dec vein,x
 dec workleft
 bne mine_loop
sim_research:
 lda buildings,x
 and #2
 beq sim_auto
 lda level,x
 cmp #5
 bcs sim_auto
 lda level,x
 asl
 asl
 asl
 clc
 adc #24
 sta workleft
 lda research,x
 clc
 adc labs,x
 cmp workleft
 bcc store_progress
 sec
 sbc workleft
 sta research,x
 inc level,x
 jsr rank_up_notice          ; invention message for the human player
 jmp sim_auto
store_progress:
 sta research,x
sim_auto:
 lda owner,x
 cmp #1
 bne sim_enemy
 lda policy,x
 and #1
 beq sim_autofort
 lda buildings,x
 and #4
 beq sim_autofort
 lda ore,x
 cmp #16
 bcc sim_autofort
 lda weapons,x
 cmp #24
 bcs sim_autofort
 lda ore,x
 sec
 sbc #4
 sta ore,x
 inc weapons,x
sim_autofort:
 lda policy,x
 and #2
 lbeq sim_render
 lda ore,x
 cmp #24
 lbcc sim_render
 lda fort,x
 cmp #5
 lbcs sim_render
 lda ore,x
 sec
 sbc #12
 sta ore,x
 inc fort,x
 jmp sim_render
sim_enemy:
 cmp #2
 lbcc sim_render
 ; AI assigns idle citizens to extraction/research instead of leaving
 ; captured provinces perpetually with one miner and no scientist.
 lda miners,x
 cmp #4
 bcs ai_worker_lab
 lda vein,x
 beq ai_worker_lab
 lda people,x
 sec
 sbc labs,x
 sec
 sbc miners,x
 cmp #11
 bcc ai_worker_lab
 inc miners,x
ai_worker_lab:
 lda buildings,x
 and #2
 beq ai_worker_done
 lda labs,x
 cmp #4
 bcs ai_worker_done
 lda people,x
 sec
 sbc labs,x
 sec
 sbc miners,x
 cmp #11
 bcc ai_worker_done
 inc labs,x
ai_worker_done:
 ; AI economy progresses naturally from mine to lab to factory.
 lda buildings,x
 and #2
 bne ai_has_lab
 lda ore,x
 cmp #6
 bcc ai_has_lab
 sec
 sbc #6
 sta ore,x
 lda buildings,x
 ora #2
 sta buildings,x
 lda #1
 sta labs,x
 sta changed
ai_has_lab:
 lda buildings,x
 and #4
 bne ai_has_factory
 lda ore,x
 cmp #14
 bcc ai_has_factory
 sec
 sbc #10
 sta ore,x
 lda buildings,x
 ora #4
 sta buildings,x
 lda #1
 sta changed
ai_has_factory:
 lda buildings,x
 and #4
 beq sim_ai_upgrade
 lda ore,x
 cmp #4
 bcc sim_ai_upgrade
 lda weapons,x
 cmp #30
 bcs sim_ai_upgrade
 lda people,x
 lsr
 cmp weapons,x
 bcc sim_ai_upgrade
 lda ore,x
 sec
 sbc #4
 sta ore,x
 inc weapons,x
sim_ai_upgrade:
 ; AI reinvests stockpile into resource throughput and defence.
 lda ore,x
 cmp #26
 bcc sim_render
 lda vein,x
 cmp #20
 bcc ai_add_fort
 lda minegrade,x
 cmp #2
 bcs ai_add_fort
 sec
 lda ore,x
 sbc #8
 sta ore,x
 inc minegrade,x
 lda #1
 sta changed
 jmp sim_render
ai_add_fort:
 lda ore,x
 cmp #40
 bcc sim_render
 lda fort,x
 cmp #4
 bcs sim_render
 lda ore,x
 sec
 sbc #12
 sta ore,x
 inc fort,x
sim_render:
 lda changed
 beq sim_next
 lda simidx
 sta sid
 jsr draw_sector
sim_next:
 ldx simidx
 inx
 cpx #12
 lbne sim_loop
 lda epoch
 cmp #5
 bcc ai_normal_rate
 lda ticks
 and #7
 bne skip_ai
 jmp ai_do_turn
ai_normal_rate:
 lda ticks
 and #15
 bne skip_ai
ai_do_turn:
 jsr ai_turn
skip_ai:
 jsr diplo_tick
 jsr panel_values
 jsr draw_score
 rts

; Neighbor rule for 4x3 island grid. src=source, destination=selected.
; Carry set only for orthogonally adjacent territories.
adjacent:
 lda source
 clc
 adc #4
 cmp selected
 beq adjacency_yes
 lda source
 sec
 sbc #4
 cmp selected
 beq adjacency_yes
 ldx source
 ldy selected
 lda grid_row,x
 cmp grid_row,y
 bne adjacency_no
 lda source
 clc
 adc #1
 cmp selected
 beq adjacency_yes
 lda source
 sec
 sbc #1
 cmp selected
 beq adjacency_yes
adjacency_no:
 clc
 rts
adjacency_yes:
 sec
 rts

player_attack:
 ldx source
 lda owner,x
 cmp #1
 bne attack_unavailable
 jsr adjacent
 bcc attack_unavailable
 ldx selected
 lda owner,x
 cmp #1
 beq attack_unavailable    ; use H for friendly transfer
 jsr break_truce           ; attacking a truce partner voids the pact
 lda #1
 sta attacking
 lda #SFX_ATTACK
 jsr sfx_play
 ldx #8
 jsr fx_shake_start
 jsr do_attack
 rts
attack_unavailable:
 lda #<msg_range
 sta PTR
 lda #>msg_range
 sta PTR+1
 jsr message
 jsr beep_no
 rts

; AI advances one eligible army per 16 strategy ticks (8 from epoch 5), prefers free sectors.
ai_turn:
 lda selected
 sta saved_selection
 lda source
 sta saved_source
 inc ai_faction
 lda ai_faction
 cmp #5
 bcc ai_faction_ok
 lda #2
 sta ai_faction
ai_faction_ok:
 inc ai_cursor
 lda ai_cursor
 cmp #12
 bcc ai_cursor_ok
 lda #0
 sta ai_cursor
ai_cursor_ok:
 lda ai_cursor
 sta ai_src
 lda #0
 sta ai_search_count
ai_source_loop:
 ldx ai_src
 lda owner,x
 cmp ai_faction
 lbne ai_next_src
 lda people,x
 cmp #18
 lbcc ai_next_src
 stx source
 ldy #0
ai_target_loop:
 sty ai_dst
 lda owner,y
 cmp ai_faction
 lbeq ai_next_dst
 cmp #1
 bne ai_target_ok
 ldx ai_faction
 lda truce,x                 ; no attacks on the human while a truce holds
 lbne ai_next_dst
ai_target_ok:
 sty selected
 jsr adjacent
 lbcc ai_next_dst
 ldy ai_dst
 lda owner,y
 beq ai_found
 ; Heavy assault estimate for tactical opposition.
 ; 3/4 troops + up to available arms + research + 1/2 assault bonus.
 ldx ai_src
 lda people,x
 lsr
 sta ai_power
 lsr
 clc
 adc ai_power
 sta ai_power
 lda weapons,x
 cmp ai_power
 bcc ai_arms_small
 lda ai_power
ai_arms_small:
 clc
 adc ai_power
 sta ai_power
 lda ai_power
 lsr
 clc
 adc ai_power
 sta ai_power
 lda level,x
 asl
 asl
 clc
 adc ai_power
 sta ai_power
 ldy ai_dst
 lda fort,y
 asl
 asl
 sta ai_defense
 lda level,y
 asl
 asl
 clc
 adc ai_defense
 sta ai_defense
 lda weapons,y
 lsr
 clc
 adc ai_defense
 clc
 adc people,y
 sta ai_defense
 lsr
 lsr
 clc
 adc ai_defense               ; the AI wants a 25% margin before it commits an assault
 bcc ai_margin_ok
 lda #255
ai_margin_ok:
 cmp ai_power
 lbcs ai_next_dst
ai_found:
 lda ai_faction
 sta attacking
 lda #1
 sta heavy
 jsr do_attack
 lda #0
 sta heavy
 jmp ai_finished
ai_next_dst:
 ldy ai_dst
 iny
 cpy #12
 lbne ai_target_loop
ai_next_src:
 inc ai_src
 lda ai_src
 cmp #12
 bcc ai_src_valid
 lda #0
 sta ai_src
ai_src_valid:
 inc ai_search_count
 lda ai_search_count
 cmp #12
 lbne ai_source_loop
ai_finished:
 lda saved_selection
 sta selected
 lda saved_source
 sta source
 jsr draw_cursor
 rts

; Shared battle engine, applied to human and CPU. source and selected adjacent.
; source loses half its troops; weapons are consumed; technology and fortification
; modify offensive / defensive strength, with no 8-bit arithmetic wrap.
do_attack:
 ldx source
 lda people,x
 cmp #8
 lbcc attack_too_small
 lsr
 sta force
 lda heavy
 beq attack_force_set
 lda force
 lsr
 clc
 adc force
 sta force
attack_force_set:
 ; remove dispatched troops from source
 lda people,x
 sec
 sbc force
 sta people,x
 ; mobilized weapons = min(force, available weapons)
 lda weapons,x
 cmp force
 bcc use_all_weapons
 lda force
use_all_weapons:
 sta usedarms
 lda weapons,x
 sec
 sbc usedarms
 sta weapons,x
 jsr march_start             ; original-art army walks to the target
 ; offense = troops + weapons + (technology * 4)
 lda level,x
 asl
 asl
 clc
 adc force
 clc
 adc usedarms
 sta offense
 lda doctrine,x
 cmp #1
 bne attack_no_doctrine
 lda level,x
 cmp #2
 bcc attack_no_doctrine
 lda offense
 clc
 adc #6
 sta offense
attack_no_doctrine:
 lda heavy
 beq attack_power_ready
 lda force
 lsr
 clc
 adc offense
 sta offense
attack_power_ready:
 ldx selected
 lda owner,x
 lbeq attack_capture
 ; defense = people + 4*fortification + 4*technology + weapons/2
 lda fort,x
 asl
 asl
 sta defense
 lda level,x
 asl
 asl
 clc
 adc defense
 sta defense
 lda weapons,x
 lsr
 clc
 adc defense
 clc
 adc people,x
 sta defense
 lda doctrine,x
 cmp #2
 bne defense_no_doctrine
 lda level,x
 cmp #2
 bcc defense_no_doctrine
 lda defense
 clc
 adc #8
 sta defense
defense_no_doctrine:
 lda offense
 cmp defense
 bcs attack_capture
 ; failed assault: defenders also lose a small number, never below 1
 lda force
 lsr
 sta casualties
 lda people,x
 sec
 sbc casualties
 bcs defense_still_alive
 lda #1
defense_still_alive:
 cmp #1
 bcs defense_pop_store
 lda #1
defense_pop_store:
 sta people,x
 ; Sieges steadily dismantle defensive equipment even if repulsed.
 lda fort,x
 beq siege_no_fort
 dec fort,x
siege_no_fort:
 lda weapons,x
 beq siege_no_arms
 dec weapons,x
siege_no_arms:
 lda attacking
 cmp #2
 bcs attack_cpu_failed
 lda #<msg_failed
 sta PTR
 lda #>msg_failed
 sta PTR+1
 jsr message
 lda #SFX_REPULSE
 jsr sfx_play
 jmp attack_redraw
attack_cpu_failed:
 lda #<msg_enemy_fail
 sta PTR
 lda #>msg_enemy_fail
 sta PTR+1
 jsr message
 jmp attack_redraw
attack_capture:
 ; capture sector and set up productive garrison
 lda owner,x
 cmp #1
 bne ac_fresh
 lda attacking
 cmp #2
 bcc ac_fresh                  ; own attack
 lda #SFX_LOST                 ; the human just lost a sector
 jsr sfx_play
 lda #2
 ldx #16
 jsr fx_flash
 ldx #6
 jsr fx_shake_start
ac_fresh:
 jsr march_capture          ; building icon appears once the army arrives
 ldx selected
 lda attacking
 sta owner,x
 lda force
 lsr
 clc
 adc #2
 sta people,x
 lda #0
 sta ore,x
 sta research,x
 lda usedarms
 sta weapons,x
 lda #0
 sta fort,x
 lda #1
 sta miners,x
 sta buildings,x
 lda #0
 sta labs,x
 sta minegrade,x
 sta policy,x                  ; captured territory loses previous owner's orders
 ldy source
 lda doctrine,y
 sta doctrine,x
 lda level,y
 beq cap_no_tech
 sec
 sbc #1
cap_no_tech:
 sta level,x
 lda attacking
 cmp #1
 bne capture_enemy_message
 lda #<msg_captured
 sta PTR
 lda #>msg_captured
 sta PTR+1
 jsr message
 lda #SFX_CAPTURE
 jsr sfx_play
 lda #13
 ldx #12
 jsr fx_flash
 jmp attack_redraw
capture_enemy_message:
 lda #<msg_rival
 sta PTR
 lda #>msg_rival
 sta PTR+1
 jsr message
attack_redraw:
 lda source
 sta sid
 jsr draw_sector
 lda selected
 sta sid
 jsr draw_sector
 ; player source can be re-selected with ENTER; never keep CPU as player source
 lda attacking
 cmp #2
 bcs atk_done
 jsr draw_panel
 jsr draw_score
atk_done:
 rts
attack_too_small:
 lda attacking
 cmp #2
 bcs atk_done
 lda #<msg_small
 sta PTR
 lda #>msg_small
 sta PTR+1
 jsr message
 jsr beep_no
 rts

; --------------------------------------------------------------------------
; Disk snapshot via KERNAL SAVE/LOAD, logical device 8 (1541 compatible).
; Safe snapshot format ML64, version 4, byte count, state, XOR and sum.
; Data is staged at $C000 so a failed validation never modifies live world.
; LOAD uses the saved header address $C000 and verifies returned length.
; Hardware and real DOS behaviour must be tested in VICE/on a 1541.
; --------------------------------------------------------------------------
prepare_snapshot:
 lda #'M'
 sta SAVE_BUFFER
 lda #'L'
 sta SAVE_BUFFER+1
 lda #'6'
 sta SAVE_BUFFER+2
 lda #'4'
 sta SAVE_BUFFER+3
 lda #4
 sta SAVE_BUFFER+4
 lda #save_count
 sta SAVE_BUFFER+5
 lda #0
 sta checksum_xor
 sta checksum_sum
 ldx #0
save_copy_loop:
 lda owner,x
 sta SAVE_BUFFER+6,x
 eor checksum_xor
 sta checksum_xor
 lda SAVE_BUFFER+6,x
 clc
 adc checksum_sum
 sta checksum_sum
 inx
 cpx #save_count
 bne save_copy_loop
 lda checksum_xor
 sta SAVE_BUFFER+6+save_count
 lda checksum_sum
 sta SAVE_BUFFER+7+save_count
 rts

setup_disk_file:
 jsr get_device
 lda #1
 ldx devnum
 ldy #0
 jsr $FFBA                      ; SETLFS sec=0: LOAD/VERIFY use X/Y, never the file header
 lda #load_filename_end-load_filename
 ldx #<load_filename
 ldy #>load_filename
 jsr $FFBD                      ; SETNAM "ML64SAVE"
 rts

setup_save_file:
 jsr get_device
 lda #1
 ldx devnum
 ldy #1
 jsr $FFBA
 lda #load_filename_end-load_filename
 ldx #<load_filename
 ldy #>load_filename
 jsr $FFBD
 rts

; Replace an old save the safe way: DOS SCRATCH on command channel 15, then a plain SAVE.
; (The "@0:" save-and-replace shortcut is unreliable on some 1541 firmware.)
scratch_save_file:
 jsr get_device
 lda #15
 ldx devnum
 ldy #15
 jsr $FFBA
 lda #scratch_name_end-scratch_name
 ldx #<scratch_name
 ldy #>scratch_name
 jsr $FFBD
 jsr $FFC0                      ; OPEN 15,dev,15,"S0:ML64SAVE"
 lda #15
 jsr $FFC3                      ; CLOSE 15
 jsr $FFCC                      ; CLRCHN
 rts

save_game:
 jsr disk_begin
 jsr save_game_io
 jmp disk_end

save_game_io:
 jsr prepare_snapshot
 jsr scratch_save_file
 jsr setup_save_file
 lda #<SAVE_BUFFER
 sta PTR
 lda #>SAVE_BUFFER
 sta PTR+1
 lda #<PTR
 ldx #<(SAVE_BUFFER+8+save_count)
 ldy #>(SAVE_BUFFER+8+save_count)
 jsr $FFD8                      ; SAVE start=$C000, end exclusive
 lbcs disk_error
 ; Read the file back with KERNAL VERIFY (LOAD with A=1) against the staged snapshot.
 jsr setup_disk_file
 lda #1
 ldx #<SAVE_BUFFER
 ldy #>SAVE_BUFFER
 jsr $FFD5
 lbcs disk_error
 jsr $FFB7                      ; READST
 and #$BF                       ; EOF ($40) is the normal outcome
 lbne disk_error
 cli
 lda #<msg_saved
 sta PTR
 lda #>msg_saved
 sta PTR+1
 jsr message
 lda #SFX_DISK
 jmp sfx_play

restore_game:
 jsr disk_begin
 jsr restore_game_io
 jmp disk_end

restore_game_io:
 jsr setup_disk_file
 lda #0
 ldx #<SAVE_BUFFER
 ldy #>SAVE_BUFFER
 jsr $FFD5                      ; LOAD relocates to $C000 regardless of header
 lbcs disk_error
 cpx #<(SAVE_BUFFER+8+save_count)
 lbne disk_error
 cpy #>(SAVE_BUFFER+8+save_count)
 lbne disk_error
 jsr $FFB7                      ; READST
 and #$BF
 lbne disk_error
 cli
 jsr validate_snapshot
 lbcc disk_error
 ; Regenerate the immutable stage terrain and video palette first.
 lda SAVE_BUFFER+6+campaign_island-owner
 sta campaign_island
 jsr load_island
 ldx #0
load_apply_loop:
 lda SAVE_BUFFER+6,x
 sta owner,x
 inx
 cpx #save_count
 bne load_apply_loop
 ; The frame rate is hardware-specific, not part of cross-region progress.
 jsr set_speed
 lda #31
 sta joylast
 lda #0
 sta load_mode
 jsr draw_static
 jsr draw_all
 jsr draw_panel
 jsr draw_score
 jsr draw_cursor
 lda #<msg_loaded
 sta PTR
 lda #>msg_loaded
 sta PTR+1
 jsr message
 lda #SFX_DISK
 jmp sfx_play

disk_error:
 cli
 lda #<msg_disk_error
 sta PTR
 lda #>msg_disk_error
 sta PTR+1
 jsr message
 jsr beep_no
 rts

validate_snapshot:
 lda SAVE_BUFFER
 cmp #'M'
 lbne snapshot_bad
 lda SAVE_BUFFER+1
 cmp #'L'
 lbne snapshot_bad
 lda SAVE_BUFFER+2
 cmp #'6'
 lbne snapshot_bad
 lda SAVE_BUFFER+3
 cmp #'4'
 lbne snapshot_bad
 lda SAVE_BUFFER+4
 cmp #4
 lbne snapshot_bad
 lda SAVE_BUFFER+5
 cmp #save_count
 lbne snapshot_bad
 lda #0
 sta checksum_xor
 sta checksum_sum
 ldx #0
snapshot_verify_loop:
 lda SAVE_BUFFER+6,x
 eor checksum_xor
 sta checksum_xor
 lda SAVE_BUFFER+6,x
 clc
 adc checksum_sum
 sta checksum_sum
 inx
 cpx #save_count
 bne snapshot_verify_loop
 lda checksum_xor
 cmp SAVE_BUFFER+6+save_count
 lbne snapshot_bad
 lda checksum_sum
 cmp SAVE_BUFFER+7+save_count
 lbne snapshot_bad
 lda SAVE_BUFFER+6+campaign_island-owner
 cmp #28
 lbcs snapshot_bad
 lda SAVE_BUFFER+6+selected-owner
 cmp #12
 lbcs snapshot_bad
 lda SAVE_BUFFER+6+source-owner
 cmp #12
 lbcs snapshot_bad
 lda SAVE_BUFFER+6+state-owner
 cmp #5
 lbcs snapshot_bad
 ldx #4
snapshot_truce:
 lda SAVE_BUFFER+6+truce-owner,x
 cmp #TRUCE_TICKS+1
 lbcs snapshot_bad
 lda SAVE_BUFFER+6+truce_cool-owner,x
 cmp #TRUCE_COOL+1
 lbcs snapshot_bad
 dex
 bpl snapshot_truce
 ldx #0
snapshot_ranges:
 lda SAVE_BUFFER+6+owner-owner,x
 cmp #5
 lbcs snapshot_bad
 lda SAVE_BUFFER+6+people-owner,x
 cmp #91
 lbcs snapshot_bad
 lda SAVE_BUFFER+6+ore-owner,x
 cmp #96
 lbcs snapshot_bad
 lda SAVE_BUFFER+6+miners-owner,x
 cmp #13
 lbcs snapshot_bad
 lda SAVE_BUFFER+6+labs-owner,x
 cmp #13
 lbcs snapshot_bad
 lda SAVE_BUFFER+6+level-owner,x
 cmp #6
 lbcs snapshot_bad
 lda SAVE_BUFFER+6+weapons-owner,x
 cmp #91
 lbcs snapshot_bad
 lda SAVE_BUFFER+6+fort-owner,x
 cmp #10
 lbcs snapshot_bad
 lda SAVE_BUFFER+6+buildings-owner,x
 cmp #8
 lbcs snapshot_bad
 lda SAVE_BUFFER+6+minegrade-owner,x
 cmp #3
 lbcs snapshot_bad
 lda SAVE_BUFFER+6+policy-owner,x
 cmp #4
 lbcs snapshot_bad
 lda SAVE_BUFFER+6+doctrine-owner,x
 cmp #3
 lbcs snapshot_bad
 inx
 cpx #12
 bne snapshot_ranges
 sec
 rts
snapshot_bad:
 clc
 rts

load_filename: !text "ML64SAVE"
load_filename_end:
scratch_name: !text "S0:ML64SAVE"
scratch_name_end:
msg_saved: !text "GAME SAVED AND VERIFIED - O SAVE I LOAD",0
msg_loaded: !text "GAME RESTORED FROM DISK",0
msg_disk_error: !text "DISK/SAVE ERROR - STATE UNCHANGED",0

; Original small-string UI (character codes match generated ASCII-indexed charset).
title_msg:   !text "MEGA-LO-MANIA 64    ",0
help_a:      !text "WASD MOVE RET BASE X RAID T ASSAULT",0
help_b:      !text "H SEND Q ROLE MRJK JOB E TRUCE U AUTO",0
help_c:      !text "V LAB G FAC P ARM F FORT B MINE O/I DISK",0
score_msg:   !text "LAND YOU:00 CPU:00   TICK:00",0
spd_msg:     !text "SPEED 2",0
epoch_msg:   !text "E00 I00",0
hud_sector:  !text "SECTOR",0
hud_owner:   !text "OWNER",0
hud_pop:     !text "PEOPLE",0
hud_ore:     !text "ORE",0
hud_vein:    !text "DEPOSIT",0
hud_tech:    !text "TECH",0
hud_mine:    !text "MINERS",0
hud_lab:     !text "LABS",0
hud_arms:    !text "WEAPONS",0
hud_base:    !text "BASE:00 F0",0
hud_build:   !text "BLD:0/0/0",0
hud_auto:    !text "AUTO:0/0",0
epoch_title_lo: !byte <age_0,<age_1,<age_2,<age_3,<age_4,<age_5,<age_6,<age_7,<age_8,<age_9
epoch_title_hi: !byte >age_0,>age_1,>age_2,>age_3,>age_4,>age_5,>age_6,>age_7,>age_8,>age_9
age_0: !text "PREHIST",0
age_1: !text "BRONZE",0
age_2: !text "IRON",0
age_3: !text "CLASSIC",0
age_4: !text "MEDIEVAL",0
age_5: !text "RENAISS",0
age_6: !text "STEAM",0
age_7: !text "INDUSTRY",0
age_8: !text "ATOMIC",0
age_9: !text "FUTURE",0
hud_doctrine: !text "ROLE:",0
doctrine_char: !byte 'I','M','D'
hud_free:    !text "FREE",0
hud_you:     !text "YOU",0
hud_cpu:     !text "RED ",0
hud_rival3:  !text "BLUE",0
hud_rival4:  !text "GOLD",0
msg_start:   !text "CONQUER THE ISLAND. ENTER SETS BASE.",0
msg_pause:   !text "PAUSED  -  SPACE TO CONTINUE",0
msg_go:      !text "STRATEGY RUNNING",0
msg_spd0:    !text "SPEED 1 - SLOW",0
msg_spd1:    !text "SPEED 2 - NORMAL",0
msg_spd2:    !text "SPEED 3 - FAST",0
msg_source:  !text "ARMY SOURCE SET. CHOOSE ADJACENT TARGET.",0
msg_reinforce: !text "REINFORCEMENTS ARRIVED IN SECTOR",0
msg_rival:   !text "ENEMY CAPTURED TERRITORY!",0
msg_enemy_fail: !text "ENEMY ASSAULT REPELLED",0
msg_denied:  !text "NOT ENOUGH RESOURCES OR IDLE PEOPLE",0
msg_range:   !text "SET OWN BASE WITH ENTER, ATTACK NEIGHBOR",0
msg_failed:  !text "ASSAULT FAILED. GROW AND RESEARCH!",0
msg_captured:!text "TERRITORY CAPTURED!",0
msg_small:   !text "NEED AT LEAST 8 PEOPLE TO ATTACK",0
msg_win:     !text "ISLAND WON! C=NEXT ISLAND  N=RESTART",0
msg_campaign_won: !text "ALL 28 ISLANDS WON! N=NEW CAMPAIGN",0
msg_stage: !text "STAGE SELECT: ENTER 01..28 (N CANCEL)",0
msg_stage_two: !text "FIRST DIGIT SET. ENTER SECOND DIGIT",0
msg_stage_error: !text "INVALID STAGE CODE - USE 01..28",0
msg_loss:    !text "DEFEAT! ALL BASES LOST. N=NEW GAME",0

; 6x5 coarse topographic mask (1 land, 0 sea). Edges create coves.
coast_mask:  !byte 0,0,1,1,1,0, 0,1,1,1,1,1, 1,1,1,1,1,1, 1,1,1,1,1,0, 0,1,1,1,0,0
coast_mask1: !byte 0,1,1,1,0,0, 1,1,1,1,0,0, 1,1,1,1,1,0, 1,1,1,1,1,1, 0,1,1,1,1,0
coast_mask2: !byte 0,0,0,1,1,0, 0,1,1,1,1,0, 1,1,1,1,1,1, 1,1,1,1,1,1, 0,0,1,1,0,0
coast_mask3: !byte 0,1,1,1,1,0, 1,1,1,1,1,0, 1,1,1,1,1,0, 0,1,1,1,1,0, 0,0,1,1,0,0
coast_mask_lo: !byte <coast_mask,<coast_mask1,<coast_mask2,<coast_mask3
coast_mask_hi: !byte >coast_mask,>coast_mask1,>coast_mask2,>coast_mask3
sector_x:   !byte 1,8,15,22,1,8,15,22,1,8,15,22
sector_y:   !byte 3,3,3,3,9,9,9,9,15,15,15,15
grid_row:   !byte 0,0,0,0,1,1,1,1,2,2,2,2
grid_col:   !byte 0,1,2,3,0,1,2,3,0,1,2,3
terrain:    !byte 1,2,3,4,4,1,2,3,5,1,4,2
; Starting populations and resources are generated from campaign indices.

; row offsets for default screen at $0400; color address = screen address+$D400.

; Campaign data: exactly 28 deterministic islands / 10 epochs, no streaming RAM.
epoch_by_island: !byte 0,0,0,1,1,1,2,2,2,3,3,3,4,4,4,5,5,5,6,6,6,7,7,7,8,8,8,9
spawn_human: !byte 0,3,8,11,4,7,1,2,0,3,8,11,4,7,1,2,0,3,8,11,4,7,1,2,0,3,8,11
spawn_cpu: !byte 11,8,3,0,7,4,10,9,11,8,3,0,7,4,10,9,11,8,3,0,7,4,10,9,11,8,3,0
spawn_rival3: !byte 3,0,0,3,0,0,0,0,3,0,0,3,0,0,0,0,3,0,0,3,0,0,0,0,3,0,0,3
spawn_rival4: !byte 8,11,11,8,3,3,3,3,8,11,11,8,3,3,3,3,8,11,11,8,3,3,3,3,8,11,11,8
sea_palette: !byte 5,5,13,5,5,12,12,14,14,15
earth_palette: !byte 13,13,7,7,8,8,10,10,15,15
world_terrain_lo: !byte <island_terrain_0,<island_terrain_1,<island_terrain_2,<island_terrain_3,<island_terrain_4,<island_terrain_5,<island_terrain_6,<island_terrain_7,<island_terrain_8,<island_terrain_9,<island_terrain_10,<island_terrain_11,<island_terrain_12,<island_terrain_13,<island_terrain_14,<island_terrain_15,<island_terrain_16,<island_terrain_17,<island_terrain_18,<island_terrain_19,<island_terrain_20,<island_terrain_21,<island_terrain_22,<island_terrain_23,<island_terrain_24,<island_terrain_25,<island_terrain_26,<island_terrain_27
world_terrain_hi: !byte >island_terrain_0,>island_terrain_1,>island_terrain_2,>island_terrain_3,>island_terrain_4,>island_terrain_5,>island_terrain_6,>island_terrain_7,>island_terrain_8,>island_terrain_9,>island_terrain_10,>island_terrain_11,>island_terrain_12,>island_terrain_13,>island_terrain_14,>island_terrain_15,>island_terrain_16,>island_terrain_17,>island_terrain_18,>island_terrain_19,>island_terrain_20,>island_terrain_21,>island_terrain_22,>island_terrain_23,>island_terrain_24,>island_terrain_25,>island_terrain_26,>island_terrain_27
world_vein_lo: !byte <island_vein_0,<island_vein_1,<island_vein_2,<island_vein_3,<island_vein_4,<island_vein_5,<island_vein_6,<island_vein_7,<island_vein_8,<island_vein_9,<island_vein_10,<island_vein_11,<island_vein_12,<island_vein_13,<island_vein_14,<island_vein_15,<island_vein_16,<island_vein_17,<island_vein_18,<island_vein_19,<island_vein_20,<island_vein_21,<island_vein_22,<island_vein_23,<island_vein_24,<island_vein_25,<island_vein_26,<island_vein_27
world_vein_hi: !byte >island_vein_0,>island_vein_1,>island_vein_2,>island_vein_3,>island_vein_4,>island_vein_5,>island_vein_6,>island_vein_7,>island_vein_8,>island_vein_9,>island_vein_10,>island_vein_11,>island_vein_12,>island_vein_13,>island_vein_14,>island_vein_15,>island_vein_16,>island_vein_17,>island_vein_18,>island_vein_19,>island_vein_20,>island_vein_21,>island_vein_22,>island_vein_23,>island_vein_24,>island_vein_25,>island_vein_26,>island_vein_27
island_terrain_0: !byte 1,2,2,3,2,3,4,3,3,4,5,5
island_vein_0: !byte 72,55,58,87,48,44,50,83,58,81,70,81
island_terrain_1: !byte 5,5,1,5,5,1,1,1,2,2,3,2
island_vein_1: !byte 64,61,74,55,62,56,60,47,74,58,50,72
island_terrain_2: !byte 3,2,3,3,4,3,4,5,5,4,5,5
island_vein_2: !byte 73,65,57,86,49,79,49,84,53,50,67,56
island_terrain_3: !byte 1,2,3,3,2,2,4,4,4,4,4,4
island_vein_3: !byte 60,79,46,63,61,69,60,79,57,49,46,60
island_terrain_4: !byte 4,4,5,1,1,5,1,2,1,1,3,3
island_vein_4: !byte 71,52,81,44,70,82,74,62,71,85,58,57
island_terrain_5: !byte 2,3,4,4,3,4,5,5,5,5,5,1
island_vein_5: !byte 61,64,71,73,53,38,42,86,66,76,61,68
island_terrain_6: !byte 1,2,2,2,3,3,4,4,3,3,4,5
island_vein_6: !byte 85,66,60,72,53,49,35,65,57,87,58,67
island_terrain_7: !byte 5,4,1,5,1,1,1,2,1,2,3,3
island_vein_7: !byte 74,75,82,63,68,55,85,83,59,44,81,49
island_terrain_8: !byte 2,2,3,4,4,4,4,5,4,5,1,1
island_vein_8: !byte 51,54,55,64,68,55,58,80,51,78,66,55
island_terrain_9: !byte 2,2,3,3,2,3,3,4,4,3,5,4
island_vein_9: !byte 56,68,63,73,77,72,82,46,53,68,57,59
island_terrain_10: !byte 5,4,1,5,1,5,1,2,2,2,3,2
island_vein_10: !byte 77,79,77,56,82,46,60,69,80,63,77,72
island_terrain_11: !byte 3,3,3,3,4,4,4,4,5,4,1,1
island_vein_11: !byte 47,60,46,69,54,43,80,53,64,51,63,51
island_terrain_12: !byte 2,1,2,2,3,2,3,3,3,3,5,4
island_vein_12: !byte 59,40,59,58,77,48,71,79,37,62,50,45
island_terrain_13: !byte 4,4,5,5,1,5,1,1,2,2,2,3
island_vein_13: !byte 76,50,50,48,49,71,76,57,52,76,75,54
island_terrain_14: !byte 2,3,3,4,3,3,5,4,4,5,5,1
island_vein_14: !byte 51,63,81,85,58,71,67,50,66,80,84,53
island_terrain_15: !byte 1,1,3,2,3,3,4,4,3,4,5,4
island_vein_15: !byte 61,71,74,73,56,71,39,52,73,69,74,58
island_terrain_16: !byte 4,4,5,5,5,5,1,1,1,1,2,2
island_vein_16: !byte 76,53,65,56,58,55,82,41,79,61,50,47
island_terrain_17: !byte 3,2,4,3,4,3,4,5,5,4,1,5
island_vein_17: !byte 85,54,43,87,64,53,80,54,70,76,81,59
island_terrain_18: !byte 2,1,3,2,2,2,4,4,4,4,4,4
island_vein_18: !byte 55,77,76,77,74,46,43,58,62,58,54,61
island_terrain_19: !byte 5,5,5,1,5,5,1,2,1,2,2,3
island_vein_19: !byte 57,75,81,71,53,68,61,45,41,43,54,71
island_terrain_20: !byte 2,2,4,3,3,4,4,5,4,4,5,5
island_vein_20: !byte 77,73,59,77,83,75,75,53,67,70,44,44
island_terrain_21: !byte 1,2,3,3,3,3,3,3,4,3,5,4
island_vein_21: !byte 75,63,62,61,80,79,73,68,54,69,45,77
island_terrain_22: !byte 5,5,1,5,1,1,1,2,2,2,3,3
island_vein_22: !byte 73,71,81,62,83,67,48,42,59,36,44,59
island_terrain_23: !byte 2,2,4,3,3,4,5,5,5,4,5,5
island_vein_23: !byte 73,61,50,57,60,69,52,57,59,68,66,66
island_terrain_24: !byte 1,1,2,3,2,2,4,3,3,4,4,4
island_vein_24: !byte 53,71,84,61,55,71,62,84,57,46,62,80
island_terrain_25: !byte 5,4,5,1,1,5,2,1,1,1,3,3
island_vein_25: !byte 72,64,37,78,60,54,56,54,43,85,61,70
island_terrain_26: !byte 3,3,4,4,3,3,5,5,5,4,5,1
island_vein_26: !byte 56,61,51,63,41,68,49,86,50,80,83,82
island_terrain_27: !byte 1,1,2,3,2,3,4,3,4,3,5,5
island_vein_27: !byte 84,58,68,51,87,37,52,78,73,75,46,73
row_lo:
!byte <$0400,<$0428,<$0450,<$0478,<$04a0,<$04c8,<$04f0,<$0518,<$0540,<$0568,<$0590,<$05b8,<$05e0,<$0608,<$0630,<$0658,<$0680,<$06a8,<$06d0,<$06f8,<$0720,<$0748,<$0770,<$0798,<$07c0
row_hi:
!byte >$0400,>$0428,>$0450,>$0478,>$04a0,>$04c8,>$04f0,>$0518,>$0540,>$0568,>$0590,>$05b8,>$05e0,>$0608,>$0630,>$0658,>$0680,>$06a8,>$06d0,>$06f8,>$0720,>$0748,>$0770,>$0798,>$07c0

; Runtime data blocks kept in ordinary RAM in executable segment.
owner:     !fill 12,0
people:    !fill 12,0
vein:      !fill 12,0
ore:       !fill 12,0
miners:    !fill 12,0
labs:      !fill 12,0
weapons:   !fill 12,0
fort:      !fill 12,0
level:     !fill 12,0
research:  !fill 12,0
buildings: !fill 12,0             ; bit0 mine, bit1 laboratory, bit2 factory
minegrade: !fill 12,0             ; mine extraction bonus, max 2
policy:    !fill 12,0             ; player auto manufacture / fortification
doctrine:  !fill 12,0             ; 0 industry, 1 attack, 2 defensive bonuses
truce:     !fill 5,0              ; v4: ticks of truce left, indexed by faction id (2..4 used)
truce_cool:!fill 5,0              ; v4: ticks until that faction negotiates again
campaign_island: !byte 0        ; 0..27
reserve:   !byte 12
load_mode: !byte 0
load_tens: !byte 0
load_ones: !byte 0
epoch:     !byte 0               ; 0..9
frames_per_tick: !byte 16
joylast:   !byte 31
music_frame: !byte 0
music_pos: !byte 0
ai_cursor: !byte 0
ai_faction: !byte 2
ai_search_count: !byte 0
ai_power:  !byte 0
ai_defense: !byte 0
selected:  !byte 0
source:    !byte 0
state:     !byte 0
frames:    !byte 0
ticks:     !byte 0
soundtime: !byte 0
ink:       !byte 1
glyph:     !byte 0
value:     !byte 0
remainder: !byte 0
tens:      !byte 0
text_x:    !byte 0
text_y:    !byte 0
text_index:!byte 0
sid:       !byte 0
basex:     !byte 0
basey:     !byte 0
tilechar:  !byte 0
territory_ink: !byte 0
dx:        !byte 0
dy:        !byte 0
simidx:    !byte 0
workleft:  !byte 0
growphase: !byte 0
changed:   !byte 0
saved_selection:!byte 0
saved_source:!byte 0
keycode:   !byte 0
ai_src:    !byte 0
ai_dst:    !byte 0
attacking: !byte 0
force:     !byte 0
usedarms:  !byte 0
offense:   !byte 0
defense:   !byte 0
casualties:!byte 0
mask:      !byte 0
heavy:     !byte 0
you_count: !byte 0
cpu_count: !byte 0
checksum_xor: !byte 0
checksum_sum: !byte 0
save_count = cpu_count+1-owner

* = $3700
!bin "../assets/cursor_sprite.bin"
* = $3740
!bin "../assets/source_sprite.bin"
* = $3800
!bin "../assets/charset.bin"

; ---- v4 engine modules, placed above the VIC bank-0 graphics ($4000..) ----
!source "engine.asm"
