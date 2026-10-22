#include "world.h"
#ifdef __CC65__
#pragma code-name ("LOWCODE")
#endif
uint8_t world_first,world_last,world_slot,world_factions;
static uint8_t *cursor;
static uint8_t saving;
static uint16_t word(const uint8_t *p) {return p[0]|((uint16_t)p[1]<<8);}
static void put(uint8_t *p,uint16_t v) {p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);}
static void span(uint16_t at,uint16_t size) {
    while(size--) {
        if(saving)*cursor++=gp_sector[at++];else gp_sector[at++]=*cursor++;
    }
}
static void transfer(void) {
    uint8_t k,active,*d;
    uint16_t n,age_count;
    if(world_slot>=16 || world_first>world_last || world_last>9 || world_last-world_first>3)return;
    cursor=(uint8_t *)(WORLD_ADDRESS+(uint16_t)world_slot*WORLD_SLOT);
    if(!saving)for(n=0;n<GP_SECTOR_BYTES;++n)gp_sector[n]=0;
    for(k=0;k<4;++k) {
        d=gp_sector+12+(uint16_t)k*24;
        if(saving) {
            *cursor++=d[4];*cursor++=d[5];
            for(n=10;n<14;++n)*cursor++=d[n];
            *cursor++=(d[6]!=255 || d[7]!=255 || d[8]!=255 || d[9]!=255) && (d[6] || d[7] || d[8] || d[9]);
        }else {
            d[4]=*cursor++;d[5]=*cursor++;
            for(n=10;n<14;++n)d[n]=*cursor++;
            active=*cursor++;n=word(d+4);
            put(d+6,active?48000:65535);put(d+8,active?0:65535);
            put(d+14,active?n-(n>>5):0);
        }
    }
    span(10,2);
    for(k=0;k<3;++k)span(0x6c+(uint16_t)k*24+4,12);
    span(0xb4,50);age_count=world_last-world_first+1;
    for(k=0;k<3;++k)span(0xe6+(uint16_t)k*20+(uint16_t)world_first*2,age_count*2);
    span(0x122,18);span(0x134,104);
    for(k=0;k<3;++k)span(0x19c+(uint16_t)k*100+(uint16_t)world_first*10,age_count*10);
    for(k=0;k<4;++k) {span(0x2c8+(uint16_t)k*11+world_first,age_count);span(0x2c8+(uint16_t)k*11+10,1);}
    span(0x2f4,20);
    for(k=0;k<4;++k) {span(0x308+(uint16_t)k*22+(uint16_t)world_first*2,age_count*2);span(0x308+(uint16_t)k*22+20,2);}
    for(k=0;k<4;++k) {span(0x360+(uint16_t)k*22+(uint16_t)world_first*2,age_count*2);span(0x360+(uint16_t)k*22+20,2);}
    span(0x3b8,70);span(0x3fe,30);span(0x41c,45);
    if(saving)while(cursor<(uint8_t *)(WORLD_ADDRESS+(uint16_t)(world_slot+1)*WORLD_SLOT))*cursor++=0;
}
void world_get(void) {saving=0;transfer();}
void world_put(void) {saving=1;transfer();}
