/* C64 game interface leaf overlay. Drawing never changes disk overlays. */
#include "game.h"
#ifdef __CC65__
#pragma code-name ("INTERFACE")
#pragma rodata-name ("INTERFACE")
#endif
extern uint16_t hw_frames(void);
extern void text(uint16_t at,const char *s,uint8_t ink);
extern void number(uint16_t at,uint16_t n,uint8_t ink);
extern uint8_t picture_inks[12],board_glyphs[144],board_inks[144],io_message;
static const char *const faction_names[4]={"RED","BLUE","GREEN","GOLD"};
#define SCR ((uint8_t *)0x0400)
#define COL ((uint8_t *)0xd800)
#define REG(a) (*(volatile uint8_t *)(a))
#define island ng_state[NG_ISLAND]
#define player ng_state[NG_HUMAN]
#define selected ng_state[NG_SELECTED]
#define category ng_state[NG_CATEGORY]
#define design ng_state[NG_DESIGN]
#define deposit ng_state[NG_DEPOSIT]
#define building ng_state[NG_BUILDING]
#define paused ng_state[NG_PAUSED]
#define tiles ng_terrain
#define owners ng_owners
#define ages ng_ages
#define populations ng_people
static uint16_t rd(uint16_t at) {return gp_sector[at]|((uint16_t)gp_sector[at+1]<<8);}
static void get(uint8_t slot) {world_slot=slot;world_get();}
static void panel(void) {
    uint8_t i,j,mode;uint16_t at,base;
    mode=ng_state[NG_PANEL];if(!mode)return;
    for(i=5;i<19;++i)for(j=25;j<40;++j) {at=(uint16_t)i*40+j;SCR[at]=32;COL[at]=1;}
    if(mode==1) {
        text(225,"ARMY / STOCK",7);
        for(i=0;i<11;++i) {
            at=265+(uint16_t)i*40;SCR[at]=i==10?'U':48+i;COL[at]=3;
            number(at+2,gp_sector[0x2c8+(uint16_t)player*11+i],7);
            if(i<10)number(at+8,rd(0x10e +(uint16_t)i*2),1);
        }
        text(705,"U/H  X ARM",3);
    }else if(mode==2) {
        text(225,"FACILITIES HP",7);
        for(i=0;i<4;++i) {
            at=265+(uint16_t)i*40;SCR[at]=48+i;COL[at]=3;
            number(at+3,(gp_sector[0x446]&(1<<i))?rd(0x3d6+(uint16_t)i*2):0,7);
        }
        text(425,"TURRET / AGE",7);
        for(i=0;i<10;++i) {
            at=465+(uint16_t)(i/2)*40+(i%2)*8;
            SCR[at]=48+i;COL[at]=3;j=gp_sector[0x3b8+i];SCR[at+2]=j==255?'-':48+j;COL[at+2]=1;
        }
        text(665,"I/O GUN 8 HEAL",3);text(705,"0 SHUTDOWN",3);
    }else {
        text(225,"FACTION / PACT",7);
        for(i=0;i<4;++i) {
            at=265+(uint16_t)i*40;SCR[at]=49+i;COL[at]=2+i;
            text(at+3,(gp_alliances[player]&(1<<i))?"ALLY":"ENEMY",1);
        }
        text(425,"L ALLIANCE",3);text(465,"RESOURCES",7);
        for(i=0;i<4;++i) {
            base=0x134+(uint16_t)i*16;at=505+(uint16_t)i*40;j=(uint8_t)rd(base+12);
            SCR[at]=49+i;COL[at]=3;number(at+2,j,1);number(at+8,j<20?rd(0x174+(uint16_t)j*2):0,7);
        }
        text(705,"[ ] DEPOSIT",3);
    }
}
void ng_draw(void) {
    uint8_t i,owner,ink,k;uint16_t at;
    REG(1)=0x35;REG(0xd020)=0;REG(0xd021)=0;
    text(0,"MEGA-LO-MANIA 64",7);text(18,ng_state[NG_HOTSEAT]?"HOTSEAT    ":"HUMAN VS AI",3);SCR[30]=48+ng_state[NG_DIFFICULTY];COL[30]=3;number(34,island+1,3);
    for(i=0;i<16;++i) {
        owner=owners[i];ink=owner<4?(uint8_t)(2+owner):5;
        at=121+(uint16_t)(i>>2)*160+(i&3)*6;
        for(k=0;k<9;++k) {SCR[at+(k/3)*40+k%3]=board_glyphs[(uint16_t)i*9+k];COL[at+(k/3)*40+k%3]=ng_ruined[i]?11:board_inks[(uint16_t)i*9+k];}
        if(tiles[i]) {number(at+120,populations[i],ink);
        SCR[at+4]=owner<4?49+owner:32;COL[at+4]=ink;
        SCR[at+44]=48+ages[i];COL[at+44]=3;}
        if(i==selected) {SCR[at]=62;COL[at]=7;}
    }
    get(selected);if(ng_state[NG_PHASE]) {
        number(625,ng_state[NG_DEPLOY]|((uint16_t)ng_state[NG_DEPLOY+1]<<8),7);
        text(665,"POOL",1);number(697,ng_state[NG_POOL]|((uint16_t)ng_state[NG_POOL+1]<<8),7);
        text(745,"START",1);number(780,ng_state[NG_START]+1,7);
    }
    text(105,"PLAYER",7);number(112,player+1,7);
    text(185,"SECTOR",1);number(192,selected+1,1);
    text(225,"IDLE",1);number(232,rd(GP_FREE),7);
    text(265,"DESIGN",1);number(272,design,3);
    text(305,"TYPE",1);number(312,category,3);
    text(345,"DEPOSIT",1);number(353,deposit+1,3);
    at=0x134 + (uint16_t)deposit*16;
    text(385,"MINERS",1);number(392,rd(at),7);
    text(425,"STOCK",1);k=(uint8_t)rd(at+12);number(432,k<20?rd(0x174 + (uint16_t)k*2):0,7);
    text(465,"INVENTORS",1);number(474,rd(0xc4),7);
    text(505,"FACTORY",1);number(514,rd(0xd8),7);
    text(545,"BLD / SLOT",1);SCR[556]=48+building;COL[556]=7;SCR[559]=48+ng_state[NG_TURRET];COL[559]=7;
    text(585,"ARMY",1);number(592,rd(0x2f4+(uint16_t)player*2),7);
    panel();
    text(760,"                                      ",6);
    if(ng_state[NG_DIP_ACTIVE]) {
        text(760,"ALLIANCE",7);text(810,faction_names[ng_state[NG_DIPLO]<4?ng_state[NG_DIPLO]:0],7);
        text(850,ng_state[NG_DIP_PROMPT]?"+ YES - NO":ng_state[NG_DIPLO+12]?"REFUSED":!ng_state[NG_DIPLO+18]?"ACCEPTED":"NEGOTIATING",7);
    }else text(760,io_message==1?"SAVED":io_message==2?"SAVE FAILED":io_message==3?"LOADED":io_message==4?"LOAD FAILED":ng_state[NG_STATUS]==NG_COMPLETE?"CAMPAIGN COMPLETE":ng_state[NG_STATUS]==NG_WON?"VICTORY - N NEXT":ng_state[NG_STATUS]==NG_LOST?"DEFEAT - N RESTART":paused?"PAUSED ":"RUNNING",7);
    text(800,ng_state[NG_PHASE]?"PREP: N ISLAND +/- MEN ENTER START":"WASD/JOY MOVE ENTER/FIRE SEND ARMY",1);
    text(840,"M/J MINE R/K RESEARCH B/V BUILD F/G MAKE",1);
    text(880,"C TYPE E AGE T BUILDING Z SLOT X ARM",1);
    text(920,"F5 SAVE F7 LOAD ? VIEW Y HOTSEAT",1);
    text(960,"U/H TROOPS I/O DEFEND 8 REPAIR Q NUKE",3);
    if(!ng_state[NG_PANEL])for(i=0;i<12;++i) {at=625+(uint16_t)(i/6)*40+i%6;SCR[at]=128+i;COL[at]=picture_inks[i];}
    /* Original army and tower art; selected sector sets their VIC position. */
    REG(0xd015)=7;REG(0xd01c)=6;REG(0xd017)=0;REG(0xd01d)=0;
    REG(0xd000)=32+(selected%4)*48;REG(0xd001)=74+(selected/4)*32;
    REG(0xd002)=242;REG(0xd003)=187;REG(0xd004)=282&255;REG(0xd005)=187;REG(0xd010)=4;
    REG(0x07f8)=0xdc;REG(0x07f9)=0xc5 + ((hw_frames()>>3)&3);REG(0x07fa)=0xc9;
    REG(0xd027)=7;REG(0xd028)=player+2;REG(0xd029)=player+2;
    REG(1)=0x34;
}
