/* Playable native development front end. No extracted content is embedded. */
#include "game.h"
#ifdef __CC65__
#pragma rodata-name ("UIRODATA")
#endif
extern uint8_t __fastcall__ hw_open(const char *name);
extern uint8_t hw_read(void);
extern void hw_close(void);
extern uint8_t hw_key(void);
extern uint16_t hw_frames(void);
extern void __fastcall__ hw_play(uint16_t count);
extern uint8_t hw_error,hw_eof,clip_voice;
extern uint8_t __fastcall__ hw_store(uint8_t slot);
extern void __fastcall__ hw_shadow(uint8_t restore);
extern uint16_t hw_crc(void);
uint8_t runtime_ready,runtime_last_key,runtime_drawn;
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
#define speed ng_state[NG_SPEED]
#define tiles ng_terrain
#define owners ng_owners
#define ages ng_ages
#define populations ng_people
#define rule ng_rule
static uint8_t source=255,cursor,dirty=1,frame_rate,loaded_clip=255,picture_inks[12],io_message;
static uint16_t stamps[16],last_service;
static char file[9]="NMAP01";
static uint16_t rd(uint16_t at) {return gp_sector[at]|((uint16_t)gp_sector[at+1]<<8);}
static void wr(uint16_t at,uint16_t value) {gp_sector[at]=(uint8_t)value;gp_sector[at+1]=(uint8_t)(value>>8);}
static void get(uint8_t slot) {world_slot=slot;world_get();}
static void save(void) {ng_cache();}
#ifdef __CC65__
#pragma code-name (push, "LOWCODE")
#endif
static void text(uint16_t at,const char *s,uint8_t ink) {
    uint8_t c,bank;bank=REG(1);REG(1)=0x36;
    while((c=(uint8_t)*s++)!=0) {SCR[at]=c;COL[at++]=ink;}
    REG(1)=bank;
}
static void number(uint16_t at,uint16_t n,uint8_t ink) {
    uint16_t divisor;
    uint8_t digit,bank;bank=REG(1);REG(1)=0x36;
    for(divisor=1000;divisor;divisor/=10) {
        digit=(uint8_t)(n/divisor);n%=divisor;
        SCR[at]=48+digit;COL[at++]=ink;
    }
    REG(1)=bank;
}
#ifdef __CC65__
#pragma code-name (pop)
#endif
static void clear(void) {uint16_t i;uint8_t bank;bank=REG(1);REG(1)=0x36;for(i=0;i<1000;++i) {SCR[i]=32;COL[i]=1;}REG(1)=bank;}
#ifdef __CC65__
#pragma code-name (push, "RUNTIME")
#endif
static uint16_t read_word(void) {uint16_t n;n=hw_read();return n|((uint16_t)hw_read()<<8);}
static uint8_t signature(const char *s) {while(*s)if(hw_read()!=(uint8_t)*s++)return 0;return !hw_error;}
static uint8_t unpack(uint8_t *dest,uint16_t left) {
    uint16_t count;uint8_t control,value;
    while(left && !hw_error) {
        control=hw_read();count=(control&128)?control-125:control+1;
        if(count>left)return 0;
        value=0;if(control&128)value=hw_read();
        while(count--) {*dest++=(control&128)?value:hw_read();--left;}
    }
    return !hw_error;
}
static uint8_t table(uint8_t *dest,uint16_t n) {while(n--)*dest++=hw_read();return !hw_error;}
#ifdef __CC65__
#pragma code-name (push, "LOWCODE")
#endif
static void filename(const char *prefix,uint8_t n) {
    uint8_t i;for(i=0;i<4;++i)file[i]=prefix[i];
    file[4]=48+n/10;file[5]=48+n%10;file[6]=0;
}
#ifdef __CC65__
#pragma code-name (pop)
#endif
#ifdef __CC65__
#pragma code-name (push, "BATTLE")
#endif
static void audio(uint8_t clip) {
    uint16_t count;
    if(clip!=loaded_clip) {
        filename("NSND",clip);
        if(!hw_open(file))return;
        if(!signature("NGS1")) {hw_close();return;}
        count=read_word();clip_voice=hw_read();
        if(!count || (count+1)/2>4346 || !unpack((uint8_t *)0xef00,(count+1)/2)) {hw_close();loaded_clip=255;return;}
        hw_close();loaded_clip=clip;
        /* Keep the length outside the shared sample cache. */
        REG(0x33f0)=(uint8_t)count;REG(0x33f1)=(uint8_t)(count>>8);REG(0x33f2)=clip_voice;
    }
    clip_voice=REG(0x33f2);hw_play(REG(0x33f0)|((uint16_t)REG(0x33f1)<<8));
}
#ifdef __CC65__
#pragma code-name (pop)
#endif
static uint8_t rules_load(void) {
    uint8_t ok;
    if(!hw_open("NGTABLE"))return 0;
    ok=signature("NGR1");
    table(gp_classes,20);table(gp_buildings,96);table(gp_patterns,270);table(gp_groups,20);
    table(gp_complexity,14);table(gp_manufacture,14);table(gp_research_points,12);table(gp_technology_points,20);
    table(gp_army_rules,66);table(gp_defence_rules,60);table(gp_combat_rules,10);table(gp_alliances,4);
    ok=ok&&!hw_error;hw_close();return ok;
}
#ifdef __CC65__
#pragma code-name (push, "GRAPHICS")
#endif
static uint8_t bank_load(void) {
    uint16_t size;uint8_t ok;
    if(!hw_open("NGCODE"))return 0;
    ok=signature("NGC1");size=read_word();
    ok=ok && size && size<=0x1b00 && unpack((uint8_t *)0xd400,size);
    hw_close();return ok;
}
#ifdef __CC65__
#pragma code-name (pop)
#pragma code-name (pop)
#endif
void gp_ensure_rare(void) {
    uint16_t size;uint8_t ok;
    if(loaded_clip==254)return;
    if(!hw_open("NGRARE")) {runtime_ready=2;while(1);}
    ok=signature("NGX1");size=read_word();
    ok=ok && size && size<=4346 && unpack((uint8_t *)0xef00,size);
    hw_close();if(!ok) {runtime_ready=2;while(1);}loaded_clip=254;
}
static void failed(void) {runtime_ready=2;clear();text(400,"NATIVE CONTENT LOAD FAILED - RESET",2);while(1);}
#ifdef __CC65__
#pragma code-name (push, "RUNTIME")
#endif
static uint8_t load_island(uint8_t resume) {
    uint8_t i,faction,count;uint16_t now;
    clear();text(400,"LOADING ORIGINAL ISLAND",1);
    filename("NMAP",island+1);
    if(!hw_open(file))return 0;
    if(!signature("NGW2")) {hw_close();return 0;}
    world_first=hw_read();world_last=hw_read();
    table(tiles,16);
    if(!unpack((uint8_t *)0x3c00,96) || !table(picture_inks,12)) {hw_close();return 0;}
    if(world_first>world_last || world_last>9 || world_last-world_first>3 || (!resume && !unpack((uint8_t *)WORLD_ADDRESS,WORLD_SLOT*16))) {hw_close();return 0;}
    hw_close();if(!resume) {design=world_first;selected=0;}source=255;
    filename("NSPR",world_first);
    if(!hw_open(file))return 0;
    i=signature("NGP1") && unpack((uint8_t *)0x3140,320);hw_close();if(!i)return 0;
    if(!resume)ng_state[NG_STATUS]=NG_PLAYING;ng_state[NG_NUKE]=255;
    count=0;for(i=0;i<16;++i)if(tiles[i] && count<4)++count;
    if(!resume) {ng_state[NG_ACTIVE]=(1<<count)-1;if(player>=count)player=0;
        ng_reset_pacts();
    }
    faction=0;
    for(i=0;i<16;++i)if(tiles[i]) {
        get(i);if(!resume)rule(26,0,0,0);
        if(!resume && faction<count) {
            for(cursor=0;cursor<11;++cursor)gp_army[cursor]=0;
            gp_army[10]=100;rule(20,faction,0,0);rule(31,1000,0,0);
            if(faction==player)selected=i;
            ++faction;
        }
        save();
    }
    now=hw_frames();for(i=0;i<16;++i)stamps[i]=now;
    last_service=now;clear();dirty=1;return 1;
}
#ifdef __CC65__
#pragma code-name (pop)
#pragma code-name (push, "GRAPHICS")
#endif
static void draw(void) {
    uint8_t i,x,y,owner,ink,k;uint16_t at;
    REG(1)=0x36;
    text(0,"MEGA-LO-MANIA 64",7);text(18,ng_state[NG_HOTSEAT]?"HOTSEAT    ":"HUMAN VS AI",3);SCR[30]=48+ng_state[NG_DIFFICULTY];COL[30]=3;number(34,island+1,3);
    for(i=0;i<16;++i) {
        owner=owners[i];ink=owner<4?(uint8_t)(2+owner):5;
        x=1+(i%4)*6;y=3+(i/4)*4;at=(uint16_t)y*40+x;
        text(at,tiles[i]?"+----+":"......",tiles[i]?ink:6);
        if(tiles[i]) {
            text(at+40,"|    |",ink);number(at+41,populations[i],1);
            text(at+80,"|    |",ink);number(at+81,ages[i],3);
            text(at+120,"+----+",ink);
        }
        if(i==selected) {SCR[at]=62;COL[at]=7;}
    }
    get(selected);text(105,"PLAYER",7);number(112,player+1,7);
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
    text(760,"                                      ",6);
    text(760,io_message==1?"SAVED":io_message==2?"SAVE FAILED":io_message==3?"LOADED":io_message==4?"LOAD FAILED":ng_state[NG_STATUS]==NG_COMPLETE?"CAMPAIGN COMPLETE":ng_state[NG_STATUS]==NG_WON?"VICTORY - N NEXT":ng_state[NG_STATUS]==NG_LOST?"DEFEAT - N RESTART":paused?"PAUSED ":"RUNNING",7);
    text(800,"WASD/JOY MOVE ENTER/FIRE SEND ARMY",1);
    text(840,"M/J MINE R/K RESEARCH B/V BUILD F/G MAKE",1);
    text(880,"C TYPE E AGE T BUILDING Z SLOT X ARM",1);
    text(920,"F5 SAVE F7 LOAD Y HOTSEAT N NEXT",1);
    text(960,"U/H TROOPS I/O DEFEND Q NUKE L ALLY",3);
    for(i=0;i<12;++i) {at=625+(uint16_t)(i/6)*40+i%6;SCR[at]=128+i;COL[at]=picture_inks[i];}
    /* Original army and tower art; selected sector sets their VIC position. */
    REG(0xd015)=7;REG(0xd01c)=6;REG(0xd017)=0;REG(0xd01d)=0;
    REG(0xd000)=32+(selected%4)*48;REG(0xd001)=74+(selected/4)*32;
    REG(0xd002)=242;REG(0xd003)=187;REG(0xd004)=282&255;REG(0xd005)=187;REG(0xd010)=4;
    REG(0x07f8)=0xdc;REG(0x07f9)=0xc5 + ((hw_frames()>>3)&3);REG(0x07fa)=0xc9;
    REG(0xd027)=7;REG(0xd028)=player+2;REG(0xd029)=player+2;
    REG(1)=0x34;dirty=0;++runtime_drawn;
}
#ifdef __CC65__
#pragma code-name (pop)
#endif
#ifdef __CC65__
#pragma code-name (push, "CODE")
#endif
#define SNAP ((uint8_t *)0x3f80)
static char save_file[7]="NSAVE0";
static uint8_t probe_header[12],probe_valid;
static uint16_t crc_byte(uint16_t crc,uint8_t value) {
    uint8_t i;crc^=(uint16_t)value<<8;
    for(i=0;i<8;++i)crc=(crc<<1)^((crc&32768)?0x1021:0);
    return crc;
}
#ifdef __CC65__
#pragma code-name (push, "RUNTIME")
#endif
static uint16_t probe_save(uint8_t slot) {
    uint16_t crc,i,sequence;uint8_t value;
    save_file[5]=48+slot;probe_valid=0;
    if(!hw_open(save_file))return 0;
    if(read_word()!=0x3f80) {hw_close();return 0;}
    crc=65535;
    for(i=0;i<10624 && !hw_error;++i) {
        value=hw_read();if(i<12)probe_header[i]=value;
        crc=crc_byte(crc,(i==6 || i==7)?0:value);
    }
    probe_valid=!hw_error && hw_eof && probe_header[0]=='N' && probe_header[1]=='G' && probe_header[2]=='S' && probe_header[3]=='V' && probe_header[4]==1 && crc==(probe_header[6]|((uint16_t)probe_header[7]<<8));
    sequence=probe_header[8]|((uint16_t)probe_header[9]<<8);hw_close();return sequence;
}
#ifdef __CC65__
#pragma code-name (pop)
#endif
static uint8_t snapshot_valid(void) {
    uint16_t expected,actual;uint8_t i,j;
    expected=SNAP[6]|((uint16_t)SNAP[7]<<8);SNAP[6]=0;SNAP[7]=0;actual=hw_crc();
    SNAP[6]=(uint8_t)expected;SNAP[7]=(uint8_t)(expected>>8);
    if(actual!=expected || SNAP[NG_ISLAND]>=28 || SNAP[NG_HUMAN]>=4 || !(SNAP[NG_ACTIVE]&(1<<SNAP[NG_HUMAN])) || SNAP[NG_ACTIVE]>15 || SNAP[NG_STATUS]>3 || SNAP[NG_PAUSED]>1 || SNAP[NG_SELECTED]>=16 || SNAP[NG_CATEGORY]>=3 || SNAP[NG_DESIGN]>=10 || SNAP[NG_DEPOSIT]>=4 || SNAP[NG_BUILDING]>=4 || SNAP[NG_HOTSEAT]>1 || SNAP[NG_DIFFICULTY]<1 || SNAP[NG_DIFFICULTY]>3)return 0;
    if(SNAP[NG_SPEED]!=1 && SNAP[NG_SPEED]!=3 && SNAP[NG_SPEED]!=9)return 0;
    for(i=0;i<4;++i) {
        if(!(SNAP[NG_ALLIES+i]&(1<<i)) || SNAP[NG_ALLIES+i]>15)return 0;
        for(j=0;j<4;++j)if(!!(SNAP[NG_ALLIES+i]&(1<<j))!=!!(SNAP[NG_ALLIES+j]&(1<<i)))return 0;
    }
    return 1;
}
static uint8_t persistence(uint8_t writing) {
    uint16_t seq0,seq1,next;uint8_t valid0,valid1,slot,i,ok,attempt;
    seq0=probe_save(0);valid0=probe_valid;seq1=probe_save(1);valid1=probe_valid;
    slot=valid1 && (!valid0 || (uint16_t)(seq1-seq0)<32768)?1:0;
    next=slot?seq1:seq0;
    if(writing) {
        if(!valid0 && !valid1) {next=0;slot=1;}++next;slot^=1;
        ng_state[0]='N';ng_state[1]='G';ng_state[2]='S';ng_state[3]='V';ng_state[4]=1;
        for(i=0;i<NG_STATE_BYTES;++i)SNAP[i]=ng_state[i];
        SNAP[8]=(uint8_t)next;SNAP[9]=(uint8_t)(next>>8);SNAP[6]=0;SNAP[7]=0;
        seq0=hw_crc();SNAP[6]=(uint8_t)seq0;SNAP[7]=(uint8_t)(seq0>>8);
        ok=hw_store(slot);if(ok) {ng_state[8]=(uint8_t)next;ng_state[9]=(uint8_t)(next>>8);}return ok;
    }
    if(!valid0 && !valid1)return 0;
    for(i=0;i<NG_STATE_BYTES;++i)SNAP[i]=ng_state[i];
    hw_shadow(0);loaded_clip=255;ok=0;
    for(attempt=0;attempt<2 && !ok;++attempt,slot^=1) {
        if((slot && !valid1) || (!slot && !valid0))continue;
        save_file[5]=48+slot;
        if(!hw_open(save_file))continue;
        read_word();ok=table(SNAP,10624) && hw_eof;hw_close();if(ok)ok=snapshot_valid();
    }
    if(!ok)hw_shadow(1);
    for(i=0;i<NG_STATE_BYTES;++i)ng_state[i]=SNAP[i];
    if(!bank_load())failed();
    for(i=0;i<4;++i)gp_alliances[i]=ng_state[NG_ALLIES+i];
    if(!load_island(1))failed();return ok;
}
#ifdef __CC65__
#pragma code-name (pop)
#endif
#ifdef __CC65__
#pragma code-name (push, "CODE")
#endif
static void command(uint8_t key) {
    uint16_t n,at;uint8_t i,target,old;
    if(key!=135 && key!=136)io_message=0;
    if(key=='W' && selected>=4)--selected,--selected,--selected,--selected;
    else if(key=='S' && selected<12)selected+=4;
    else if(key=='A' && selected%4)--selected;
    else if(key=='D' && selected%4<3)++selected;
    else if(key==' ')paused^=1;
    else if(key>='1' && key<='3')speed=key=='1'?1:key=='2'?3:9;
    else if(key=='P' && ng_state[NG_HOTSEAT]) {do {player=(player+1)%4;}while(!(ng_state[NG_ACTIVE]&(1<<player)));}
    else if(key=='Y')ng_state[NG_HOTSEAT]^=1;
    else if(key==133)ng_state[NG_DIFFICULTY]=ng_state[NG_DIFFICULTY]%3+1;
    else if(key==135)io_message=persistence(1)?1:2;
    else if(key==136)io_message=persistence(0)?3:4;
    else if(key=='C')category=(category+1)%3;
    else if(key=='E')design=design==world_last?world_first:design+1;
    else if(key=='T')building=(building+1)%4;
    else if(key=='[')deposit=(deposit+3)%4;
    else if(key==']')deposit=(deposit+1)%4;
    else if(key=='N' && ng_state[NG_STATUS]==NG_WON) {++island;if(!load_island(0))failed();}
    else if(key=='N' && ng_state[NG_STATUS]>=NG_LOST) {ng_new();if(!load_island(0))failed();}
    else {
        get(selected);old=(uint8_t)rd(0x3fe);n=rd(GP_FREE);
        if(key=='L')ng_negotiate(old);
        else if(key=='Q' && old==player)ng_state[NG_NUKE]=selected;
        else if(key==13 && ng_state[NG_NUKE]<16) {
            i=ng_state[NG_NUKE];ng_state[NG_NUKE]=255;ng_break(old);ng_launch(i,selected,player,0);
        }else if(key==13) {
            if(source==255) {if(tiles[selected] && rd(0x2f4+(uint16_t)player*2))source=selected;}
            else {
                target=selected;i=source;source=255;
                if(tiles[target]) {
                    ng_break(old);ng_move(i,target,player);audio(0);
                }
            }
        }else if(old==player) {
            at=0x134 + (uint16_t)deposit*16;
            if(key=='M' && n && (gp_sector[0x432]&(1<<deposit)))rule(2,rd(at)+1,deposit,0);
            if(key=='J' && rd(at))rule(2,rd(at)-1,deposit,0);
            if(key=='R' && n && !(rd(0x122+(uint16_t)category*2)&(1<<design)) && (design<6 || (gp_sector[0x446]&4)))rule(17,rd(0xc4)+1,category,design);
            if(key=='K' && rd(0xc4))rule(17,rd(0xc4)-1,category,design);
            at=0x6c + (uint16_t)(building-1)*24;
            if(key=='B' && building && n && !(gp_sector[0x446]&(1<<building)) && rd(0x418)>=(building==1?3:building==2?5:4))rule(10,rd(at+4)+1,building,0);
            if(key=='V' && building && rd(at+4))rule(10,rd(at+4)-1,building,0);
            if(key=='F' && n && (gp_sector[0x446]&8))rule(13,rd(0xd8)+1,category,design);
            if(key=='G' && rd(0xd8))rule(13,rd(0xd8)-1,category,design);
            if(key=='U' && n>=10 && rd(0x2f4+(uint16_t)player*2)<=240) {
                for(i=0;i<11;++i)gp_army[i]=0;gp_army[10]=10;
                wr(GP_POP,rd(GP_POP)-10);rule(0,n-10,0,0);rule(20,player,0,0);
            }
            if(key=='H') {rule(28,player,0,0);rule(29,0,0,0);}
            if(key=='X')ng_arm(design);
            if(key=='I')ng_defend(design,building,ng_state[NG_TURRET]);
            if(key=='O')rule(36,ng_state[NG_TURRET],building,0);
            if(key=='Z')ng_state[NG_TURRET]=(ng_state[NG_TURRET]+1)%4;
            if(key=='0' && (gp_sector[0x448]&16))ng_shutdown();
            save();
        }
    }
    dirty=1;
}
#ifdef __CC65__
#pragma code-name (pop)
#endif
static void service(uint16_t now) {
    uint16_t elapsed;
    if((uint16_t)(now-last_service)<4)return;
    last_service=now;cursor=(cursor+1)&15;
    elapsed=(uint16_t)(now-stamps[cursor])*10/frame_rate;stamps[cursor]=now;
    if(paused || ng_state[NG_STATUS]!=NG_PLAYING || !elapsed)return;
    elapsed*=speed;if(!cursor)ng_clock(elapsed);
    if(tiles[cursor]) {get(cursor);ng_step(elapsed);}
    if(cursor==15)ng_outcome();
    if(cursor==selected || cursor==15)dirty=1;
}
void runtime_main(void) {
    uint8_t key;
    frame_rate=REG(0x02a6)?50:60;
    if(!bank_load() || !rules_load())failed();
    ng_new();if(!load_island(0))failed();
    runtime_ready=1;
    while(1) {
        key=hw_key();if(key) {command(key);runtime_last_key=key;}service(hw_frames());
        if(ng_event) {key=ng_event;ng_event=0;audio((key&8)?7:(key&1)?11:(key&4)?13:(key&2)?7:(key&32)?12:0);}
        if(dirty)draw();
    }
}
