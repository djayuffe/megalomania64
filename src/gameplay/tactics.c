/* Original AI tactical choices. Pure leaf overlay; resident code applies
 * plans after returning, allowing equipment and rare-rule overlay switches. */
#include "core.h"
#ifdef __CC65__
#pragma code-name ("TACTICS")
#endif
static uint16_t r(const uint8_t *p) {return p[0]|((uint16_t)p[1]<<8);}
static void w(uint8_t *p,uint16_t n) {p[0]=(uint8_t)n;p[1]=(uint8_t)(n>>8);}
static uint16_t draw(uint16_t bound) {
    gp_request[0]=7;w(gp_request+2,bound);gp_dispatch();return r(gp_request+12);
}
static uint8_t defence_available(uint8_t age) {
    uint8_t i,e,cost;uint16_t at;
    if(r(gp_defence_rules+40+(uint16_t)age*2)>r(gp_sector+GP_FREE))return 0;
    if(r(gp_sector+0xfa+(uint16_t)age*2))return 1;
    if(age>=4 || !(r(gp_sector+0x124)&((uint16_t)1<<age)))return 0;
    at=0x200+(uint16_t)age*10;
    for(i=0;i<10;i+=2) {e=gp_sector[at+i];cost=gp_sector[at+i+1];
        if(e!=255 && (e>=20 || r(gp_sector+GP_STOCKS+(uint16_t)e*2)<cost))return 0;
    }
    return 1;
}
/* DOS 16B4:0A60: random building and turret, preserve retaliation weapons,
 * prefer up to two nuclear defenders, otherwise install a higher-age weapon.
 * Returning a plan lets resident code perform overlay-changing payments. */
void gp_defence_plan(void) {
    uint8_t present[4],n,b,slot,old,count,i,age,first,last;uint16_t at;
    gp_plan[0]=255;if(!r(gp_sector+0x2fc))return;
    n=0;b=4;while(b) {--b;if(gp_sector[0x446]&(1<<b))present[n++]=b;}
    if(!n)return;b=present[draw(n)];slot=(uint8_t)draw(r(gp_buildings+(uint16_t)b*24+20));
    at=r(gp_buildings+(uint16_t)b*24+22)+slot;old=gp_sector[at];if(old==8)return;
    count=0;for(i=0;i<10;++i)if(gp_sector[0x3b8+i]==8)++count;
    age=255;if(count<2 && defence_available(8))age=8;
    if(age==255) {
        first=(uint8_t)r(gp_request+14);last=(uint8_t)r(gp_request+28);i=last+1;
        while(i>first) {--i;if(i!=8 && defence_available(i)) {age=i;break;}}
    }
    if(age==255 || (old!=255 && age!=8 && age<=old))return;
    gp_plan[0]=b;gp_plan[1]=slot;gp_plan[2]=age;
}

/* 16B4:168A: deficits use the original double-indexed cap table and
 * personality percentages, including their 16-bit multiplication wrap. */
void gp_repair_plan(void) {
    uint8_t buildings[4],n,b;uint16_t deficits[4],cap,hp,target;
    gp_plan[0]=255;if(!r(gp_sector+0x2fc))return;
    n=0;b=3;while(b!=255) {if(gp_sector[0x446]&(1<<b)) {
        cap=r(gp_repair_caps+(uint16_t)b*20+r(gp_sector+0x418)*2);
        target=(uint16_t)(cap*r(gp_personality+16+(uint16_t)b*2))/100;
        hp=r(gp_sector+0x3d6+(uint16_t)b*2);
        if(hp<target) {buildings[n]=b;deficits[n++]=target-hp;}
    }else b>>=1; /* DOS halves the index on the absent-facility branch. */
        --b;
    }
    if(!n)return;b=(uint8_t)draw(n);gp_plan[0]=buildings[b];w(gp_plan+4,deficits[b]);
}
