/* Playable native development front end. No extracted content is embedded. */
#include "world.h"
#ifdef __CC65__
#pragma rodata-name ("UIRODATA")
#endif
extern uint8_t __fastcall__ hw_open(const char *name);
extern uint8_t hw_read(void);
extern void hw_close(void);
extern uint8_t hw_key(void);
extern uint16_t hw_frames(void);
extern void __fastcall__ hw_play(uint16_t count);
extern uint8_t hw_error,clip_voice;
uint8_t runtime_ready,runtime_last_key,runtime_drawn;
#define SCR ((uint8_t *)0x0400)
#define COL ((uint8_t *)0xd800)
#define REG(a) (*(volatile uint8_t *)(a))
static uint8_t island,player,selected,source=255,category,design,deposit,building=1,paused,speed=1,tiles[16];
static uint8_t cursor,dirty=1,frame_rate,loaded_clip=255;
static uint16_t stamps[16],last_service;
static uint16_t random_seed=0x1991;
static uint8_t owners[16],ages[16],picture_inks[12];
static uint16_t populations[16];
static char file[9]="NMAP01";
static uint16_t rd(uint16_t at) {return gp_sector[at]|((uint16_t)gp_sector[at+1]<<8);}
static void wr(uint16_t at,uint16_t value) {gp_sector[at]=(uint8_t)value;gp_sector[at+1]=(uint8_t)(value>>8);}
static void rule(uint8_t op,uint16_t a,uint16_t b,uint16_t c) {
    uint8_t i;
    for(i=0;i<GP_REQ_BYTES;++i)gp_request[i]=0;
    gp_request[0]=op;gp_request[2]=(uint8_t)a;gp_request[3]=(uint8_t)(a>>8);
    gp_request[4]=(uint8_t)b;gp_request[5]=(uint8_t)(b>>8);
    gp_request[6]=(uint8_t)c;gp_request[7]=(uint8_t)(c>>8);
    gp_request[10]=(uint8_t)random_seed;gp_request[11]=(uint8_t)(random_seed>>8);
    gp_request[26]=(uint8_t)rd(0x3fe);gp_request[28]=world_last;gp_request[30]=3;
    gp_dispatch();random_seed=gp_request[10]|((uint16_t)gp_request[11]<<8);
}
static void get(uint8_t slot) {world_slot=slot;world_get();}
static void save(void) {
    world_put();owners[world_slot]=(uint8_t)rd(0x3fe);
    ages[world_slot]=(uint8_t)rd(0x418);populations[world_slot]=rd(GP_POP);
}
#ifdef __CC65__
#pragma code-name (push, "LOWCODE")
#endif
static void text(uint16_t at,const char *s,uint8_t ink) {
    uint8_t c;
    while((c=(uint8_t)*s++)!=0) {SCR[at]=c;COL[at++]=ink;}
}
static void number(uint16_t at,uint16_t n,uint8_t ink) {
    uint16_t divisor;
    uint8_t digit;
    for(divisor=1000;divisor;divisor/=10) {
        digit=(uint8_t)(n/divisor);n%=divisor;
        SCR[at]=48+digit;COL[at++]=ink;
    }
}
#ifdef __CC65__
#pragma code-name (pop)
#endif
static void clear(void) {uint16_t i;for(i=0;i<1000;++i) {SCR[i]=32;COL[i]=1;}}
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
static uint8_t rules_load(void) {
    uint8_t ok;
    if(!hw_open("NGTABLE"))return 0;
    ok=signature("NGR1");
    table(gp_classes,20);table(gp_buildings,96);table(gp_patterns,270);table(gp_groups,20);
    table(gp_complexity,14);table(gp_manufacture,14);table(gp_research_points,12);table(gp_technology_points,20);
    table(gp_army_rules,66);table(gp_defence_rules,60);table(gp_alliances,4);
    ok=ok&&!hw_error;hw_close();return ok;
}
static void failed(void) {runtime_ready=2;clear();text(400,"NATIVE CONTENT LOAD FAILED - RESET",2);while(1);}
static uint8_t load_island(void) {
    uint8_t i,faction;uint16_t now;
    clear();text(400,"LOADING ORIGINAL ISLAND",1);
    filename("NMAP",island+1);
    if(!hw_open(file))return 0;
    if(!signature("NGW2")) {hw_close();return 0;}
    world_first=hw_read();world_last=hw_read();
    table(tiles,16);
    if(!unpack((uint8_t *)0x3c00,96) || !table(picture_inks,12)) {hw_close();return 0;}
    if(world_first>world_last || world_last>9 || world_last-world_first>3 || !unpack((uint8_t *)WORLD_ADDRESS,WORLD_SLOT*16)) {hw_close();return 0;}
    hw_close();design=world_first;source=255;selected=0;
    filename("NSPR",world_first);
    if(!hw_open(file))return 0;
    i=signature("NGP1") && unpack((uint8_t *)0x3140,320);hw_close();if(!i)return 0;
    faction=0;
    for(i=0;i<16;++i)if(tiles[i]) {
        get(i);rule(26,0,0,0);
        if(faction<2) {
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
#pragma code-name (push, "GRAPHICS")
#endif
static void draw(void) {
    uint8_t i,x,y,owner,ink,k;uint16_t at;
    text(0,"MEGA-LO-MANIA 64  NATIVE RULES",7);number(34,island+1,3);
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
    text(545,"FACILITY",1);number(554,building,3);
    text(585,"ARMY",1);number(592,rd(0x2f4+(uint16_t)player*2),7);
    text(760,paused?"PAUSED ":"RUNNING",paused?2:5);
    text(800,"WASD MOVE  M/J MINERS  R/K INVENTORS",1);
    text(840,"C TYPE E AGE T FACILITY B/V BUILDERS",1);
    text(880,"F/G FACTORY X ARM ENTER MOVE P PLAYER",1);
    text(920,"[ ] DEPOSIT SPACE PAUSE 1/2/3 SPEED",1);
    text(960,"U DEPLOY H RETURN N ISLAND Z VOICE",3);
    for(i=0;i<12;++i) {at=625+(uint16_t)(i/6)*40+i%6;SCR[at]=128+i;COL[at]=picture_inks[i];}
    /* Original army and tower art; selected sector sets their VIC position. */
    REG(0xd015)=7;REG(0xd01c)=6;REG(0xd017)=0;REG(0xd01d)=0;
    REG(0xd000)=32+(selected%4)*48;REG(0xd001)=74+(selected/4)*32;
    REG(0xd002)=242;REG(0xd003)=187;REG(0xd004)=282&255;REG(0xd005)=187;REG(0xd010)=4;
    REG(0x07f8)=0xdc;REG(0x07f9)=0xc5 + ((hw_frames()>>3)&3);REG(0x07fa)=0xc9;
    REG(0xd027)=7;REG(0xd028)=player+2;REG(0xd029)=player+2;
    dirty=0;++runtime_drawn;
}
#ifdef __CC65__
#pragma code-name (pop)
#endif
#ifdef __CC65__
#pragma code-name (push, "RUNTIME")
#endif
static void command(uint8_t key) {
    uint16_t n,at;uint8_t i,target,old,crew;
    if(key=='W' && selected>=4)--selected,--selected,--selected,--selected;
    else if(key=='S' && selected<12)selected+=4;
    else if(key=='A' && selected%4)--selected;
    else if(key=='D' && selected%4<3)++selected;
    else if(key==' ')paused^=1;
    else if(key>='1' && key<='3')speed=key=='1'?1:key=='2'?3:9;
    else if(key=='Z')audio(11);
    else if(key=='P')player=(player+1)%2;
    else if(key=='C')category=(category+1)%3;
    else if(key=='E')design=design==world_last?world_first:design+1;
    else if(key=='T')building=building==3?1:building+1;
    else if(key=='[')deposit=(deposit+3)%4;
    else if(key==']')deposit=(deposit+1)%4;
    else if(key=='N') {island=(island+1)%28;if(!load_island())failed();}
    else {
        get(selected);old=(uint8_t)rd(0x3fe);n=rd(GP_FREE);
        if(key==13) {
            if(source==255) {if(tiles[selected] && rd(0x2f4+(uint16_t)player*2))source=selected;}
            else {
                target=selected;i=source;source=255;
                if(tiles[target] && ((i/4==target/4 && (i+1==target || target+1==i)) || i+4==target || target+4==i)) {
                    get(i);rule(28,player,0,0);save();get(target);rule(20,player,0,0);save();
                    get(i);rule(20,player,0,0);save();audio(0);
                }
            }
        }else if(old==player) {
            at=0x134 + (uint16_t)deposit*16;
            if(key=='M' && n && (gp_sector[0x432]&(1<<deposit)))rule(2,rd(at)+1,deposit,0);
            if(key=='J' && rd(at))rule(2,rd(at)-1,deposit,0);
            if(key=='R' && n && !(rd(0x122+(uint16_t)category*2)&(1<<design)) && (design<6 || (gp_sector[0x446]&4)))rule(17,rd(0xc4)+1,category,design);
            if(key=='K' && rd(0xc4))rule(17,rd(0xc4)-1,category,design);
            at=0x6c + (uint16_t)(building-1)*24;
            if(key=='B' && n && !(gp_sector[0x446]&(1<<building)) && rd(0x418)>=(building==1?3:building==2?5:4))rule(10,rd(at+4)+1,building,0);
            if(key=='V' && rd(at+4))rule(10,rd(at+4)-1,building,0);
            if(key=='F' && n && (gp_sector[0x446]&8))rule(13,rd(0xd8)+1,category,design);
            if(key=='G' && rd(0xd8))rule(13,rd(0xd8)-1,category,design);
            if(key=='U' && n>=10 && rd(0x2f4+(uint16_t)player*2)<=240) {
                for(i=0;i<11;++i)gp_army[i]=0;gp_army[10]=10;
                wr(GP_POP,rd(GP_POP)-10);rule(0,n-10,0,0);rule(20,player,0,0);
            }
            if(key=='H') {rule(28,player,0,0);rule(29,0,0,0);}
            if(key=='X' && design!=8 && rd(0x2f4+(uint16_t)player*2)<250) {
                crew=gp_army_rules[44+(uint16_t)design*2];at=0x10e + (uint16_t)design*2;
                if(n>crew && (rd(0x126)&(1<<design))) {
                    if(design<4) {
                        for(i=0;i<10;++i)gp_recipe[i]=gp_sector[0x264 + (uint16_t)design*10+i];
                        rule(5,1,0,0);target=gp_request[12];
                    }else {target=rd(at)!=0;if(target)wr(at,rd(at)-1);}
                    if(target) {
                        wr(GP_POP,rd(GP_POP)-crew);rule(0,n-crew,0,0);
                        for(i=0;i<11;++i)gp_army[i]=0;gp_army[design]=1;rule(20,player,0,0);
                    }
                }
            }
            save();
        }
    }
    dirty=1;
}
#ifdef __CC65__
#pragma code-name (pop)
#endif
static void service(uint16_t now) {
    uint16_t elapsed;uint8_t owner;
    if((uint16_t)(now-last_service)<4)return;
    last_service=now;cursor=(cursor+1)&15;
    elapsed=(uint16_t)(now-stamps[cursor])*10/frame_rate;stamps[cursor]=now;
    if(paused || !tiles[cursor] || !elapsed)return;
    get(cursor);owner=(uint8_t)rd(0x3fe);elapsed*=speed;
    if(owner<4) {rule(1,elapsed,0,0);rule(3,elapsed,0,0);rule(11,elapsed,0,0);rule(15,elapsed,0,0);rule(14,elapsed,0,0);rule(27,elapsed,0,0);}
    rule(21,0,0,0);rule(31,elapsed,0,0);rule(9,0,0,0);save();
    if(cursor==selected || cursor==15)dirty=1;
}
void runtime_main(void) {
    uint8_t key;
    frame_rate=REG(0x02a6)?50:60;
    if(!rules_load() || !load_island())failed();
    runtime_ready=1;
    while(1) {key=hw_key();if(key) {command(key);runtime_last_key=key;}service(hw_frames());if(dirty)draw();}
}
