; --------------------------------------------------------------------------
; Raster interrupt engine.
;  * Stage 0 fires on line IRQ_LINE once per frame: bumps `vblank`, samples
;    joystick port 2 (before the KERNAL keyboard scan can disturb $DC00),
;    advances SID music/SFX, then chains into the KERNAL IRQ ($EA31) so the
;    keyboard buffer and jiffy clock keep working.
;  * Stages 1..BAR_COUNT only run while the title screen is up: each one
;    paints one raster bar (border + background) and arms the next line.
;    These exit through $EA81 (register restore + RTI only).
; The CIA timer IRQ is switched off so exactly one IRQ per frame is taken.
; --------------------------------------------------------------------------
irq_install:
 sei
 lda #$7f
 sta $dc0d                   ; CIA1: no interrupt sources
 sta $dd0d                   ; CIA2: no NMI sources
 lda $dc0d                   ; acknowledge anything pending
 lda $dd0d
 lda #<irq_handler
 sta $0314
 lda #>irq_handler
 sta $0315
 lda #IRQ_LINE
 sta $d012
 sta irq_line
 lda $d011
 and #$7f                    ; raster compare bit 8 = 0
 sta $d011
 lda #$ff
 sta $d019                   ; clear VIC flags
 lda #$01
 sta $d01a                   ; raster IRQ only
 lda #0
 sta irq_stage
 sta title_active
 cli
 rts

irq_handler:
 lda $d019
 and #1
 beq irq_not_ours
 lda #$ff
 sta $d019                   ; acknowledge raster IRQ
 lda irq_stage
 bne irq_bar
 inc vblank
 lda #$ff
 sta $dc00                   ; no keyboard column selected: pins show only the joystick
 lda $dc00
 and #31
 sta joy_raw
 jsr sound_tick              ; SFX gate timer + music sequencer
 lda title_active
 beq irq_not_ours
 lda vblank                  ; title: arm the wobbling raster-bar stack
 and #31
 tax
 lda bar_wave,x
 sta irq_line
 sta $d012
 lda #1
 sta irq_stage
irq_not_ours:
 jmp $ea31                   ; KERNAL: keyboard scan, jiffy clock, pops regs, RTI

irq_bar:
 ldx irq_stage               ; 1..BAR_COUNT paint, BAR_COUNT+1 restores
 cpx #BAR_COUNT+1
 bcs irq_bar_last
 lda bar_color-1,x
 sta $d020
 sta $d021
 inx
 stx irq_stage
 lda irq_line
 clc
 adc #BAR_SPACING
 sta irq_line
 sta $d012
 jmp $ea81
irq_bar_last:
 lda #6
 sta $d020                   ; back to the game's blue frame
 sta $d021
 lda #IRQ_LINE
 sta $d012
 sta irq_line
 lda #0
 sta irq_stage
 jmp $ea81

; Sleep until the next vertical blank. Needs interrupts enabled.
wait_frame:
 lda vblank
wf_spin:
 cmp vblank
 beq wf_spin
 rts
