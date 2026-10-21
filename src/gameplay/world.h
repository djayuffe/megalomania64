#ifndef MLM_WORLD_H
#define MLM_WORLD_H
#include "core.h"
#define WORLD_SLOT 656
#ifndef WORLD_ADDRESS
#define WORLD_ADDRESS 0x4000
#endif
extern uint8_t world_first,world_last,world_slot;
/* The runtime owns $4000-$68ff. The normal audit build does not call these. */
void world_get(void);
void world_put(void);
#endif
