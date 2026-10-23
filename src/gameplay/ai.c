/* Original personality-weighted economy plan, DOS 16B4:18F7..1BA8.
 * Pure leaf overlay: no disk calls or calls to another overlay. */
#include "core.h"
#ifdef __CC65__
#pragma code-name ("AI")
#endif
uint8_t gp_personality[56],gp_plan[28];
static uint16_t r(const uint8_t *p) {return p[0]|((uint16_t)p[1]<<8);}
static void w(uint8_t *p,uint16_t n) {p[0]=(uint8_t)n;p[1]=(uint8_t)(n>>8);}
void gp_economy_plan(void) {
    uint16_t n,sum,kind,age,element,part,weight,total;uint8_t k,*p;
    age=r(gp_sector+0x418);total=r(gp_plan+26);
    n=r(gp_personality+2);sum=0;w(gp_plan+2,65535);
    if(!(gp_sector[0x446]&2) && gp_request[24]!=27 && age>=3) {
        part=n/2;w(gp_plan+2,part);sum+=part;n-=part;
    }
    part=n/4;
    for(k=0;k<4;++k) {
        p=gp_sector+0x134+(uint16_t)k*16;w(gp_plan+4+(uint16_t)k*2,65535);
        element=r(p+12);
        if(element<20 && r(p+14)) {
            kind=gp_classes[element];
            if((kind==2 && (gp_sector[0x446]&2)) || (kind==1 && age>=1)) {
                w(gp_plan+4+(uint16_t)k*2,part);sum+=part;
            }
        }
    }
    w(gp_plan,sum?sum:65535);if(sum)total+=r(gp_personality+2);
    /* Research and manufacture each split their weight between the missing
     * prerequisite building and an existing or pending task. */
    for(k=0;k<2;++k) {
        weight=r(gp_personality+4+(uint16_t)k*2);n=weight;sum=0;
        p=gp_plan+12+(uint16_t)k*6;w(p+2,65535);
        if(!(gp_sector[0x446]&(k?8:4)) && gp_request[24]!=27 && age>=(k?4:5)) {
            part=n/2;w(p+2,part);sum+=part;n-=part;
        }
        w(p+4,65535);
        if(r(gp_sector+(k?0xd2:0xbe))!=65535 || r(gp_sector+(k?0x430:0x428))) {w(p+4,n);sum+=n;}
        w(p,sum?sum:65535);if(sum)total+=weight;
    }
    w(gp_plan+24,r(gp_plan+24)+r(gp_personality+8));
    w(gp_plan+26,total+r(gp_personality+8));
}

/* 16B4:1BA9/1D51/1FF4: consume the population and personality denominators
 * sequentially. Each multiply deliberately wraps to a 16-bit intermediate.
 * Goal selection happens before this leaf routine; existing research and
 * production goals follow the original no-reselection branches. */
static void task(uint8_t op,uint16_t n,uint16_t b,uint16_t c) {
    if(op==13)w(gp_request+8,r(gp_sector+0xd6));
    gp_request[0]=op;w(gp_request+2,n);w(gp_request+4,b);w(gp_request+6,c);gp_dispatch();
}
static uint16_t draw(uint16_t bound) {task(7,bound,0,0);return r(gp_request+12);}
static uint8_t goal(uint16_t base,uint16_t *category,uint16_t *age) {
    uint16_t sum,n,mask,weight;uint8_t k,choices;
    sum=0;
    for(k=0;k<3;++k)if(r(gp_sector+base+(uint16_t)k*2))sum+=r(gp_personality+10+(uint16_t)k*2)+1;
    if(!sum)return 0;n=draw(sum);
    for(k=0;k<3;++k)if(r(gp_sector+base+(uint16_t)k*2)) {
        weight=r(gp_personality+10+(uint16_t)k*2)+1;if(n<weight)break;n-=weight;
    }
    *category=k;mask=r(gp_sector+base+(uint16_t)k*2);choices=0;
    for(k=0;k<10;++k)if(mask&((uint16_t)1<<k))++choices;
    n=draw(choices);k=10;do {--k;if(mask&((uint16_t)1<<k)) {if(!n)break;--n;}}while(k);
    *age=k;return 1;
}
/* DOS 11B9:1262 and CS0:C54C. Research probes consume RNG even though
 * no recipe is installed; this order matters to subsequent AI decisions. */
void gp_economy_scan(void) {
    uint16_t age,first,last,category,mask,at;uint8_t i;
    first=r(gp_request+6);last=r(gp_request+28);
    for(i=0;i<16;++i)gp_sector[0x422+i]=0;
    for(age=first;age<=last && age<10;++age)if(age<6 || (gp_sector[0x446]&4)) {
        category=3;while(category) {--category;mask=(uint16_t)1<<age;
            if(r(gp_sector+0x122+category*2)&mask)continue;
            task(12,0,category,age);
            if(r(gp_request+12)) {at=0x422+category*2;w(gp_sector+at,r(gp_sector+at)|mask);w(gp_sector+0x428,r(gp_sector+0x428)+1);}
        }
    }
    for(age=first;age<=last && age<10;++age)if(age>=4 && (gp_sector[0x446]&8)) {
        category=3;while(category) {--category;mask=(uint16_t)1<<age;
            if(!(r(gp_sector+0x122+category*2)&mask))continue;
            at=0x19c+category*100+age*10;for(i=0;i<10;++i)gp_recipe[i]=gp_sector[at+i];
            task(4,0,0,0);
            if(r(gp_request+12)) {at=0x42a+category*2;w(gp_sector+at,r(gp_sector+at)|mask);w(gp_sector+0x430,r(gp_sector+0x430)+1);}
        }
    }
}
void gp_economy_allocate(void) {
    uint16_t remaining,total,weight,budget,group,part,n,free,category,age;uint8_t g,k,at;
    remaining=r(gp_sector+GP_POP);total=r(gp_plan+26);
    for(g=0;g<3;++g) {
        at=g==0?0:g==1?12:18;group=r(gp_plan+at);
        if(group==65535)continue;
        weight=r(gp_personality+2+(uint16_t)g*2);
        if(!total || !group)continue;
        budget=(uint16_t)(remaining*weight)/total;remaining-=budget;total-=weight;w(gp_plan+26,total);
        for(k=0;k<(g?2:5);++k) {
            part=r(gp_plan+at+2+(uint16_t)k*2);if(part==65535)continue;
            n=group?(uint16_t)(budget*part)/group:0;budget-=n;group-=part;
            free=r(gp_sector+GP_FREE);
            if(!g) {
                free+=r(gp_sector+(k?0x134+(uint16_t)(k-1)*16:0x70));
                if(n>free)n=free;
                task(k?2:10,n,k?k-1:1,0);
            }else if(!k) {
                free+=r(gp_sector+0x70+(uint16_t)g*24);if(n>free)n=free;
                task(10,n,g+1,0);
            }else {
                category=r(gp_sector+(g==1?0xbe:0xd2));age=r(gp_sector+(g==1?0xc0:0xd4));
                if(category>=3 || age>=10) {
                    if(!goal(g==1?0x422:0x42a,&category,&age))continue;
                    if(g==2)w(gp_sector+0xd6,5);
                }
                free+=r(gp_sector+(g==1?0xc4:0xd8));if(n>free)n=free;
                task(g==1?17:13,n,category,age);
            }
        }
    }
}


/* 16B4:1831: stop selecting a design whose required deposit is exhausted.
 * This is not mining allocation: the original clears the known-design bit
 * and cancels manufacture of that design, releasing its workers. */
void gp_prune_design(void) {
    uint16_t category,age,first,last,at,known,mask,free;uint8_t i,j,e;
    first=r(gp_request+6);last=r(gp_request+28);category=draw(3);age=first+draw(last-first+1);
    known=0x122+category*2;mask=(uint16_t)1<<age;if(!(r(gp_sector+known)&mask))return;
    at=0x19c+category*100+age*10;
    for(i=0;i<10;++i)gp_recipe[i]=gp_sector[at+i];task(4,0,0,0);if(r(gp_request+12))return;
    for(i=0;i<10;i+=2) {
        e=gp_sector[at+i];if(e==255)continue;
        for(j=0;j<4;++j)if(r(gp_sector+0x140+(uint16_t)j*16)==e)break;
        if(j==4)return;
        if(!r(gp_sector+0x142+(uint16_t)j*16)) {
            if(r(gp_sector+0xd2)==category && r(gp_sector+0xd4)==age) {
                free=r(gp_sector+GP_FREE)+r(gp_sector+0xd8);w(gp_sector+0xd8,0);task(0,free,0,0);
                for(j=0;j<8;++j)gp_sector[0xde + j]=0;
                w(gp_sector+0xda,65535);w(gp_sector+0xdc,65535);w(gp_sector+0xd2,65535);
            }
            w(gp_sector+known,r(gp_sector+known)&~mask);return;
        }
    }
}
