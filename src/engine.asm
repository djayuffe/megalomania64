; ==========================================================================
; MEGA-LO-MANIA 64 v4 engine modules. Lives above the VIC bank-0 graphics
; ($0000-$3FFF) so the original code/data area keeps its room.
; Code and data here are NOT part of the save snapshot (see main.asm).
; ==========================================================================
IRQ_LINE = 250               ; vertical-blank work line
BAR_COUNT = 16               ; title raster bars
BAR_SPACING = 3              ; raster lines per bar
CHORD_FRAMES = 4             ; stable frames before a FIRE+direction chord fires

* = $4000
!source "irq.asm"
!source "joystick.asm"
!source "title.asm"
!source "diplomacy.asm"
!source "inventions.asm"
!source "develop.asm"
!source "tables.asm"
!source "engine_data.asm"
