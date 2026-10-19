; --------------------------------------------------------------------------
; Original-art sprites, down-converted from the 1991 sheets (tools/orig_convert.py).
;   sprite 2  marching army   4 walk frames at $3200-$32FF (pointers $C8-$CB), 2x2 expanded
;   sprite 3  building icon   1 frame at $3300 (pointer $CC), shown on a conquered sector
; Both are multicolour: %01 black ($D025), %10 sprite colour = owner colour, %11 grey ($D026).
; Per-epoch frames live in orig_army / orig_build ($7F40..) and are copied into VIC bank 0
; whenever the epoch changes (orig_load_epoch, called from set_border).
; --------------------------------------------------------------------------
ARMY_RAM   = $3200
BUILD_RAM  = $3300
MARCH_LEN  = 32                 ; frames per march
CAP_LEN    = 64                 ; frames the building icon stays up

orig_init:
 lda #$0c
 sta $d01c                      ; sprites 2,3 multicolour
 lda #0
 sta $d025
 lda #15
 sta $d026
 lda #4
 sta $d017
 sta $d01d                      ; the walking army is drawn double size
 lda #$c8
 sta $07fa
 lda #$cc
 sta $07fb
 lda #0
 sta march_t
 sta cap_t
 sta cap_pending
 lda $d015
 and #$f3
 sta $d015                   ; marching army and building icon off
 rts

; Copy this epoch's 4 army frames and building icon into sprite RAM. Preserves A, X, Y.
orig_load_epoch:
 pha
 txa
 pha
 tya
 pha
 lda epoch
 cmp #10
 bcc ole_ok
 lda #9
ole_ok:
 tax
 lda army_off_hi,x
 sta CPTR+1
 lda army_off_lo,x
 sta CPTR
 ldy #0
ole_army:
 lda (CPTR),y
 sta ARMY_RAM,y
 iny
 bne ole_army
 lda epoch
 cmp #10
 bcc ole_b
 lda #9
ole_b:
 tax
 lda build_off_hi,x
 sta CPTR+1
 lda build_off_lo,x
 sta CPTR
 ldy #63
ole_build:
 lda (CPTR),y
 sta BUILD_RAM,y
 dey
 bpl ole_build
 pla
 tay
 pla
 tax
 pla
 rts

; Start the marching animation from `source` to `selected`, coloured for `attacking`.
; Preserves A, X, Y.
march_start:
 pha
 txa
 pha
 tya
 pha
 ldx source
 lda sector_x,x
 asl
 asl
 asl
 clc
 adc #32
 sta mx
 sta march_x0
 lda sector_y,x
 asl
 asl
 asl
 clc
 adc #58
 sta my
 sta march_y0
 ldx selected
 lda sector_x,x
 asl
 asl
 asl
 clc
 adc #32
 sta march_x1
 lda sector_y,x
 asl
 asl
 asl
 clc
 adc #58
 sta march_y1
 lda #0
 sta mx_f
 sta my_f
 ; step = (end - start) * 8, 16-bit signed: hi = whole pixels/frame, lo = fraction
 lda march_x1
 sec
 sbc march_x0
 sta mdx_f
 lda #0
 sbc #0
 sta mdx_i
 jsr march_x8
 lda march_y1
 sec
 sbc march_y0
 sta mdy_f
 lda #0
 sbc #0
 sta mdy_i
 jsr march_y8
 ldx attacking
 lda own_col,x
 sta $d029                   ; sprite 2 colour
 lda mx
 sta $d004
 lda my
 sta $d005
 lda #$c8
 sta $07fa
 lda #MARCH_LEN
 sta march_t
 lda $d015
 ora #4
 sta $d015
 pla
 tay
 pla
 tax
 pla
 rts

march_x8:
 ldx #3
mx8:
 asl mdx_f
 rol mdx_i
 dex
 bne mx8
 rts
march_y8:
 ldx #3
my8:
 asl mdy_f
 rol mdy_i
 dex
 bne my8
 rts

; A sector was just captured: raise the building icon once the army has arrived.
; Preserves A, X, Y.
march_capture:
 pha
 txa
 pha
 ldx selected
 lda sector_x,x
 asl
 asl
 asl
 clc
 adc #32
 sta cap_x
 lda sector_y,x
 asl
 asl
 asl
 clc
 adc #58
 sta cap_y
 ldx attacking
 lda own_col,x
 sta cap_col
 lda #1
 sta cap_pending
 pla
 tax
 pla
 rts

; Frame IRQ (from fx_tick): advance the march and the building icon.
orig_tick:
 lda march_t
 beq ot_cap
 dec march_t
 lda mx_f
 clc
 adc mdx_f
 sta mx_f
 lda mx
 adc mdx_i
 sta mx
 sta $d004
 lda my_f
 clc
 adc mdy_f
 sta my_f
 lda my
 adc mdy_i
 sta my
 sta $d005
 lda march_t
 lsr
 lsr
 and #3
 clc
 adc #$c8
 sta $07fa                   ; walk cycle
 lda march_t
 bne ot_done
 lda $d015
 and #$fb
 sta $d015                   ; arrived
ot_cap:
 lda cap_pending
 beq ot_icon                  ; (march_t is 0 here: the army has arrived)
 lda #0
 sta cap_pending
 lda #CAP_LEN
 sta cap_t
 lda cap_x
 clc
 adc #26
 sta $d006                   ; bottom-right of the tile: keeps the garrison count readable
 lda cap_y
 clc
 adc #14
 sta $d007
 lda cap_col
 sta $d02a                   ; sprite 3 colour
 lda #$cc
 sta $07fb
 lda $d015
 ora #8
 sta $d015
 rts
ot_icon:
 lda cap_t
 beq ot_done
 dec cap_t
 beq ot_off
 cmp #16
 bcs ot_done
 and #2                      ; blink out over the last 16 frames
 beq ot_hide
 lda $d015
 ora #8
 sta $d015
 rts
ot_hide:
 lda $d015
 and #$f7
 sta $d015
 rts
ot_off:
 lda $d015
 and #$f7
 sta $d015
ot_done:
 rts

army_off_lo:
 !byte <orig_army, <(orig_army+256), <(orig_army+512), <(orig_army+768), <(orig_army+1024)
 !byte <(orig_army+1280), <(orig_army+1536), <(orig_army+1792), <(orig_army+2048), <(orig_army+2304)
army_off_hi:
 !byte >orig_army, >(orig_army+256), >(orig_army+512), >(orig_army+768), >(orig_army+1024)
 !byte >(orig_army+1280), >(orig_army+1536), >(orig_army+1792), >(orig_army+2048), >(orig_army+2304)
build_off_lo:
 !byte <orig_build, <(orig_build+64), <(orig_build+128), <(orig_build+192), <(orig_build+256)
 !byte <(orig_build+320), <(orig_build+384), <(orig_build+448), <(orig_build+512), <(orig_build+576)
build_off_hi:
 !byte >orig_build, >(orig_build+64), >(orig_build+128), >(orig_build+192), >(orig_build+256)
 !byte >(orig_build+320), >(orig_build+384), >(orig_build+448), >(orig_build+512), >(orig_build+576)

march_t:     !byte 0
cap_t:       !byte 0
cap_pending: !byte 0
cap_x:       !byte 0
cap_y:       !byte 0
cap_col:     !byte 0
mx:          !byte 0
my:          !byte 0
mx_f:        !byte 0
my_f:        !byte 0
mdx_f:       !byte 0
mdx_i:       !byte 0
mdy_f:       !byte 0
mdy_i:       !byte 0
march_x0:    !byte 0
march_y0:    !byte 0
march_x1:    !byte 0
march_y1:    !byte 0

; Print this island's original name (11 chars, from MEGA.EXE) at column 20 of row 0.
print_island_name:
 lda #<island_names
 sta PTR
 lda #>island_names
 sta PTR+1
 ldx campaign_island
 beq pin_go
pin_add:
 lda PTR
 clc
 adc #12
 sta PTR
 bcc pin_nc
 inc PTR+1
pin_nc:
 dex
 bne pin_add
pin_go:
 lda #20
 sta text_x
 lda #0
 sta text_y
 lda #1
 sta ink
 jmp print_text
