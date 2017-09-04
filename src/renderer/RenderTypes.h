/*
 * Eidolon Biomedical Framework
 * Copyright (C) 2016-7 Eric Kerfoot, King's College London, all rights reserved
 * 
 * This file is part of Eidolon.
 *
 * Eidolon is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 * 
 * Eidolon is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License along
 * with this program (LICENSE.txt).  If not, see <http://www.gnu.org/licenses/>
 */

#ifndef RENDERTYPES_H
#define RENDERTYPES_H

#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <cerrno>
#include <string>
#include <fstream>
#include <sstream>
#include <iostream>
#include <cstring>
#include <cmath>
#include <vector>
#include <map>
#include <algorithm>
#include <utility>
#include <limits>
#include <stdexcept>

#ifdef WIN32
  typedef void* _WId;
  #define WIN32_LEAN_AND_MEAN
  #include <windows.h>
  #include <tchar.h>
  #ifdef RENDER_EXPORT
  #  define DLLEXPORT __declspec( dllexport )
  #else
  #  define DLLEXPORT __declspec( dllimport )
  #endif
  #define PLATFORM_ID "Windows"
  #pragma warning(disable:4244) // disable double->float conversion complaint
  #pragma warning(disable:4250) // disable inheritance via dominance complaint
  #pragma warning(disable:4996) // disable strerror warning
  #pragma warning(disable:4100) // disable unreferenced formal parameter warning
#elif defined(__APPLE__)
  #include <unistd.h>
  #include <pthread.h>
  #include <sys/mman.h>
  #include <sys/stat.h>
  #include <sys/time.h>
  #include <sys/posix_shm.h>
  #include <fcntl.h>
  #define MAXSHMNAMLEN PSHMNAMLEN
  #define DLLEXPORT
  #define PLATFORM_ID "OSX"
  typedef long _WId;
#else
  #include <unistd.h>
  #include <pthread.h>
  #include <sys/mman.h>
  #include <sys/stat.h>
  #include <fcntl.h>
  #include <limits.h>
  #define MAXSHMNAMLEN NAME_MAX
  #define DLLEXPORT
  #define PLATFORM_ID "Linux"
  typedef unsigned long _WId;
#endif

#define dPI 3.141592653589793238462
#define fPI 3.141592f
#define fEPSILON 1.0e-10f
#define dEPSILON 1.0e-10

#define _HASH(h,v,s) (((h)<<(s)|((h)>>((sizeof(h)<<3)-(s))))^(v))

#define DBGOUT(c) do { std::cout << c << std::endl; std::cout.flush(); } while(0)

#define SAFE_DELETE(p) do { if((p)!=NULL){ delete (p); (p)=NULL; } } while(0)

namespace RenderTypes {

// various string names
static const char* platformID=PLATFORM_ID;
static const char* parentPIDVar="PARENTPID";
static const char* RenderParamGroup="RenderParam";

// platform-independent basic type definitions
typedef int i32;
typedef long long i64;
typedef unsigned char u8;
typedef unsigned int u32;
typedef unsigned long long u64;

// specific type definitions which are meaningful for data structures and the rendering systems
typedef u32 sval; // size value, fixed at 32bits even on 64bit platforms
typedef double real; // real value data type for internal code and file formats
typedef u32 rgba; // 32bit color data type
typedef u32 indexval; // index value data type for internal code and file formats, may differ from sval in future if larger indices are needed

static const real realInf=std::numeric_limits<real>::infinity();

template<typename T> T _min(const T& a, const T& b) { return a<b ? a : b; }
template<typename T> T _max(const T& a, const T& b) { return a>b ? a : b; }

template<typename T> T clamp(const T& val, const T& minval, const T& maxval)
{
	if(val>maxval)
		return maxval;
	if(val<minval)
		return minval;
	
	return val;
}

template<typename T> T lerpXi(const T& val, const T& minv, const T& maxv)
{
	return minv==maxv ? val : (val-minv)/(maxv-minv);
}

template<typename V,typename T> T lerp(const V& val, const T& v1, const T& v2)
{
	return v1+(v2-v1)*val;
}

template<typename T> int compT( const T& t1, const T& t2)
{
	if(t2<t1)
		return 1;
	if(t1<t2)
		return -1;

	return 0;
}

template<typename T> int compV(const void* t1, const void* t2)
{
	return compT<T>(*((T*)t1),*((T*)t2));
}

template<typename T> int sortTupleFirstCB(const void* v1, const void* v2)
{
	return compT(((T*)v1)->first,((T*)v2)->first);
}

template<typename T> int sortTupleSecondCB(const void* v1, const void* v2)
{
	return compT(((T*)v1)->second,((T*)v2)->second);
}

template<typename T> int sortTupleThirdCB(const void* v1, const void* v2)
{
	return compT(((T*)v1)->third,((T*)v2)->third);
}

template<typename T> int sortTupleFourthCB(const void* v1, const void* v2)
{
	return compT(((T*)v1)->fourth,((T*)v2)->fourth);
}

/// Returns true if `v1' and `v2' are within 'dEPSILON' of one another
inline bool equalsEpsilon(real v1, real v2)
{
	return fabs(v1-v2)<=dEPSILON;
}

/// Returns true if `v' is NaN
inline bool isNan(real v)
{
	volatile real vv=v; // must be volatile to prevent optimizations
	return vv!=vv; // NaN is the only value not equal to itself
}

inline real frand()
{
	return real(rand())/real(RAND_MAX);
}

inline real fround(real r)
{
	return floor(0.5+r);
}

inline std::string getPIDStr()
{
#ifdef WIN32
	DWORD self=GetCurrentProcessId();
#else
	pid_t self=getpid();
#endif

	std::ostringstream out;
	out << self;
	return out.str();
}

inline std::string getPPIDStr()
{
#ifdef WIN32
	DWORD self=0;
#else
	pid_t self=getppid();
#endif
	std::ostringstream out;
	out << self;
	return out.str();
}

inline bool isParentProc()
{
	const char* parentpid=getenv(parentPIDVar);
	return parentpid==NULL || std::string(parentpid)==getPIDStr();
}

template<typename T> T swapEndianN(T t)
{
	union {T v; u8 b[sizeof(T)]; } src,dst;
	src.v=t;
	for(size_t x=0;x<sizeof(T);x++)
		dst.b[x]=src.b[sizeof(T)-x-1];
	return dst.v;
}

template<typename T> T swapEndian32(T t)
{
	union {T v; u8 b[4]; } src,dst;
	src.v=t;
	dst.b[0]=src.b[3];
	dst.b[1]=src.b[2];
	dst.b[2]=src.b[1];
	dst.b[3]=src.b[0];
	return dst.v;
}

template<typename T> T swapEndian64(T t)
{
	union {T v; u8 b[8]; } src,dst;
	src.v=t;
	dst.b[0]=src.b[7];
	dst.b[1]=src.b[6];
	dst.b[2]=src.b[5];
	dst.b[3]=src.b[4];
	dst.b[4]=src.b[3];
	dst.b[5]=src.b[2];
	dst.b[6]=src.b[1];
	dst.b[7]=src.b[0];
	return dst.v;
}

template<typename F,typename S,typename T>
class triple
{
public:
		F first;
		S second;
		T third;

		triple() : first(),second(),third() {}
		triple(const F& first,const S& second, const T& third) : first(first),second(second), third(third) {}
		triple(const triple<F,S,T>& t) : first(t.first),second(t.second),third(t.third) {}
};

template<typename F,typename S,typename T,typename U>
class quadruple
{
public:
		F first;
		S second;
		T third;
		U fourth;

		quadruple() : first(),second(),third(), fourth() {}
		quadruple(const F& first,const S& second, const T& third, const U& fourth) : first(first),second(second), third(third),fourth(fourth) {}
		quadruple(const quadruple<F,S,T,U>& t) : first(t.first),second(t.second),third(t.third),fourth(t.fourth) {}
};

typedef std::pair<indexval,indexval> indexpair;
typedef std::pair<real,real> realpair;
typedef triple<real,real,real> realtriple;
typedef std::pair<indexval,realtriple> indextriple;
typedef triple<sval,sval,real> intersect;

template<typename T>
void bswap(T& a, T& b)
{
	u8 tmp,*aa=(u8*)&a,*bb=(u8*)&b;
	for(size_t i=0;i<sizeof(T);i++){
		tmp=aa[i];
		aa[i]=bb[i];
		bb[i]=tmp;
	}
}

/// This type is used with the TIMING and TIMINGBLOCK macros to time routine calls and code blocks, printing a time delta value to stdout
class TimingObject
{
public:
	clock_t start,stop;
	double delta;
	bool doPrint;
	bool entered;
	std::string label;

	TimingObject(const std::string& label, bool doPrint=true) : delta(0),doPrint(doPrint), entered(false), label(label)
	{ 
#ifdef WIN32
		this->label=label.substr(label.find_last_of("::")+1);
#endif

		start=clock(); 
		if(doPrint){
			std::cout << this->label << std::endl;
			std::cout.flush();
		}
	}

	~TimingObject(){ stopTiming(); }

	void stopTiming()
	{
		stop=clock();
		delta=double(stop-start)/CLOCKS_PER_SEC;
		if(doPrint){
			std::cout << label << " dT (s) = " << delta << std::endl;
			std::cout.flush();
		}
	}

	bool loopOnce()
	{
		if(entered)
			return false;

		entered=true;
		return true;
	}
};

#define TIMING TimingObject __functimer(__FUNCTION__)
#define TIMINGBLOCK(label) for(TimingObject __blockobj(label);__blockobj.loopOnce();)
 
#ifdef WIN32
  #define MutexType CRITICAL_SECTION
  #define trylock_mutex(m) (TryEnterCriticalSection(m)!=0)
  #define lock_mutex EnterCriticalSection
  #define unlock_mutex LeaveCriticalSection
  #define destroy_mutex DeleteCriticalSection
#else
  #define MutexType pthread_mutex_t
  #define trylock_mutex(m) (pthread_mutex_trylock(m)==0)
  #define lock_mutex pthread_mutex_lock
  #define unlock_mutex pthread_mutex_unlock
  #define destroy_mutex pthread_mutex_destroy
#endif

/// Simple mutex type allowing locking and attempted locking with timeout
class Mutex
{
	MutexType _mutex;

public:
	class Locker
	{
	protected:
		Mutex *parent;
		bool runblock;

	public:
		Locker(Mutex* p, real timeout=0.0) : parent(p) { runblock=parent->lock(timeout); }

		~Locker() { if(parent)parent->release(); }

		bool loopOnce()
		{
			if(!runblock)
				return false;

			runblock=false;
			return true;
		}
	};

	Mutex()
	{
#ifdef WIN32
		InitializeCriticalSection(&_mutex);
#else
		pthread_mutexattr_t attrs;
		pthread_mutexattr_init(&attrs);
		pthread_mutexattr_settype(&attrs,PTHREAD_MUTEX_RECURSIVE);
		pthread_mutex_init(&_mutex,&attrs);
#endif
	}

	~Mutex() { destroy_mutex(&_mutex); }

	/**
	 * Acquire the mutex lock. If `timeout' is >0 try for that length of time in seconds to acquire the lock. Returns true
	 * if `timeout'<=0 or the lock was acquired in the time given, false if the time elapsed without getting the lock.
	 */
	bool lock(real timeout=0.0)
	{
		if(timeout>0){
			clock_t start=clock();
			real delta=0;
			bool result=false;

			while(!result && delta<timeout){
				result=trylock_mutex(&_mutex);
				delta=real(clock()-start)/CLOCKS_PER_SEC;
			}

			return result;
		}
		else{
			lock_mutex(&_mutex);
			return true;
		}
	}
	
	/// Releases the mutex lock
	void release() { unlock_mutex(&_mutex); }
};

#define critical(m) for(Mutex::Locker __locker__=Mutex::Locker(m);__locker__.loopOnce();)
#define trylock(m,timeout) for(Mutex::Locker __locker__=Mutex::Locker(m,timeout);__locker__.loopOnce();)


/// Defines the figure types which the Figure class and subclasses are capable of representing
enum FigureType
{
	FT_LINELIST      =  0, // list of line segments
	FT_POINTLIST     =  1, // list of discrete points
	FT_TRILIST       =  2, // list of triangles
	FT_TRISTRIP      =  3, // strip of triangles 
	FT_BB_POINT      =  4, // BBT_POINT billboard points
	FT_BB_FIXED_PAR  =  5, // BBT_ORIENTED_SELF billboard oriented along an axis of rotation
	FT_BB_FIXED_PERP =  6, // BBT_PERPENDICULAR_SELF billboard oriented along a normal of rotation
	FT_GLYPH         =  7, // list of points represented by glyph meshes
//	FT_INTERPFIGURE  =  8, // figure which interpolates between two given other figures
	FT_RIBBON        =  8, // list of lines represented by ribbons
	FT_TEXVOLUME     =  9, // 3D texture volume
	FT_TEXT          = 10  // text billboard 
};

/// Possible blending modes as defined in materials, these define what operation is applied to the 
/// pixels being rendered into the scene when a figure is rendered. 
enum BlendMode
{
	BM_ALPHA,
	BM_COLOR,
	BM_ADD,
	BM_MOD,
	BM_REPLACE
};

/** Possible texture formats defining the how many channels pixels have and how wide. For the full
  * color component formats (RGBA, RGB, ARGB) all the channels from an input color are used when
  * filling a texture of these types. For the luminance and/or alpha formats, the red component is
  * used for luminance and the alpha component for alpha. 
  */
enum TextureFormat
{
	TF_RGB24,     // 24-bit RGB pixels PF_R8G8B8
	TF_RGBA32,    // 32-bit RGBA pixels PF_R8G8B8A8
	TF_ARGB32,    // 32-bit ARGB pixels PF_A8R8G8B8
	TF_LUM8,      // 8-bit greyscale, no alpha PF_L8
	TF_LUM16,     // 16-bit greyscale, no alpha PF_L16
	TF_ALPHA8,    // 8-bit alpha mask, no greyscale PF_A8
	TF_ALPHALUM8, // 4-bit alpha, 4-bit greyscale PF_A4L4
	TF_UNKNOWN    // Any other format from the renderer that's not used/understood
};

enum ProgramType
{
	PT_VERTEX  =0,
	PT_FRAGMENT=1,
	PT_GEOMETRY=2
};

enum HAlignType
{
	H_LEFT,
	H_RIGHT,
	H_CENTER
};

enum VAlignType
{
	V_TOP,
	V_BOTTOM,
	V_CENTER
};



#ifdef WIN32
  std::string formatLastErrorMsg(); // Windows error reporting helper
#endif

// OS X shared memory cleanup stuff

//extern std::vector<std::string> sharednamelist; // list of shared names to delete on exit
//void addShared(const std::string& name);
//void cleanupShared();


void initSharedDir(const std::string& path);
std::string getSharedDir();
void addShared(const std::string& name);
void unlinkShared(const std::string& name);

/*****************************************************************************************************************************/
/* Math Objects */
/*****************************************************************************************************************************/

/// Represents a Red-Green-Blue-Alpha color with float channels. Note the lack of virtual members implies no vtable pointer.
class color
{
	float _r,_g,_b,_a;

public:
	/// Fast linear interpolation between rgba values
	static rgba interpolate(real val,rgba left, rgba right)
	{
		u32 bf = u32(val*255);
		u32 af = 255 - bf;
		
		u32 al = (left & 0x00ff00ff);
		u32 ah = (left & 0xff00ff00) >> 8;
		u32 bl = (right & 0x00ff00ff);
		u32 bh = (right & 0xff00ff00) >> 8;
		
		u32 ml = (al * af + bl * bf);
		u32 mh = (ah * af + bh * bf);
		
		return (mh & 0xff00ff00) | ((ml & 0xff00ff00) >> 8);
	}
	
	color(float r=1.0f, float g=1.0f, float b=1.0f, float a=1.0f) : _r(r),_g(g),_b(b),_a(a)
	{}

	color(const color & c) : _r(c.r()),_g(c.g()),_b(c.b()),_a(c.a())
	{}
	
	color(const rgba& c) : _r(u8(c>>24)/255.0f), _g(u8(c>>16)/255.0f), _b(u8(c>>8)/255.0f), _a(u8(c)/255.0f)
	{}

	float r() const { return _r; }
	float g() const { return _g; }
	float b() const { return _b; }
	float a() const { return _a; }

	float r(float val) { _r=val; return _r; }
	float g(float val) { _g=val; return _g; }
	float b(float val) { _b=val; return _b; }
	float a(float val) { _a=val; return _a; }
	
	void setBuff(float *v) const { v[0]=_r; v[1]=_g; v[2]=_b; v[3]=_a; }

	/// Convert this color to a 32-bit red-green-blue-alpha value suitable for certain renderer input values
	rgba toRGBA() const
	{
		rgba result=u8(_r*255);
		result=(result<<8)|u8(_g*255);
		result=(result<<8)|u8(_b*255);
		result=(result<<8)|u8(_a*255);
		return result;
	}

	/// Linearly interpolate between `this' and `col', val==0.0 yields `this', val==1.0 yields `col'.
	color interpolate(real val,const color& col) const
	{
		if(val>=1)
			return col;

		if(val<=0)
			return *this;

		real val1=1.0f-val;
		return color(_r*val1+col.r()*val,_g*val1+col.g()*val,_b*val1+col.b()*val,_a*val1+col.a()*val);
	}

	color unitClamp()
	{
		return color(clamp(_r,0.0f,1.0f),clamp(_g,0.0f,1.0f),clamp(_b,0.0f,1.0f),clamp(_a,0.0f,1.0f));
	}

	bool operator == (const color & c) const { return equalsEpsilon(r(),c.r()) && equalsEpsilon(g(),c.g()) && equalsEpsilon(b(),c.b()) && equalsEpsilon(a(),c.a()); }
	bool operator != (const color & c) const { return !((*this)==c); }
	
	color operator * (const color & c) const { return color(_r*c.r(),_g*c.g(),_b*c.b(),_a*c.a()); }
	color operator * (real r) const { return color(_r*r,_g*r,_b*r,_a*r); }

	color operator + (const color & c) const { return color(_r+c.r(),_g+c.g(),_b+c.b(),_a+c.a()); }
	color operator + (real r) const { return color(_r+r,_g+r,_b+r,_a+r); }	

	color operator - (const color & c) const { return color(_r-c.r(),_g-c.g(),_b-c.b(),_a-c.a()); }
	color operator - (real r) const { return color(_r-r,_g-r,_b-r,_a-r); }

	bool operator < (const color &c) const { return (_r-dEPSILON)<c.r() && (_g-dEPSILON)<c.g() && (_b-dEPSILON)<c.b() && (_a-dEPSILON)<c.a(); }
	bool operator > (const color &c) const { return (_r+dEPSILON)>c.r() && (_g+dEPSILON)>c.g() && (_b+dEPSILON)>c.b() && (_a+dEPSILON)>c.a(); }

	friend std::ostream& operator << (std::ostream &out, const color &c)
	{
		return out << "color(" << c.r() << ", " << c.g() << ", " << c.b() << ", " << c.a() << ")";
	}
};

/// The all-important 3-space vector type. Note the lack of virtual members implies no vtable pointer.
class vec3
{
	real _x,_y,_z;

public:
	/// Construct a vector by setting all components to `val'.
	vec3(real val=0) : _x(val),_y(val),_z(val) {}
	/// Construct a vector with the given components
	vec3(real x, real y, real z=0) : _x(x),_y(y),_z(z) {}
	/// Copy constructor
	vec3(const vec3 & v) : _x(v.x()),_y(v.y()),_z(v.z()) {}

	real x() const { return _x; }
	real y() const { return _y; }
	real z() const { return _z; }

	real x(real v) { _x=v; return _x; }
	real y(real v) { _y=v; return _y; }
	real z(real v) { _z=v; return _z; }
	
	void setBuff(float *v) const { v[0]=_x; v[1]=_y; v[2]=_z; }

	vec3 operator + (const vec3& v) const { return vec3(_x+v.x(),_y+v.y(),_z+v.z()); }
	vec3 operator - (const vec3& v) const { return vec3(_x-v.x(),_y-v.y(),_z-v.z()); }
	vec3 operator * (const vec3& v) const { return vec3(_x*v.x(),_y*v.y(),_z*v.z()); }
	vec3 operator / (const vec3& v) const { return vec3(_x/v.x(),_y/v.y(),_z/v.z()); }
	vec3 operator + (real v) const { return vec3(_x+v,_y+v,_z+v); }
	vec3 operator - (real v) const { return vec3(_x-v,_y-v,_z-v); }
	vec3 operator * (real v) const { return vec3(_x*v,_y*v,_z*v); }
	vec3 operator / (real v) const { return vec3(_x/v,_y/v,_z/v); }
	vec3 operator - () const { return vec3(-_x,-_y,-_z); }
	
	/// Return a vector with the absolute value of each component of `this'.
	vec3 abs() const { return vec3(fabs(_x),fabs(_y),fabs(_z)); }
	/// Return a vector with each component of `this' inverted or 0 if already 0. 
	vec3 inv() const { return vec3(_x!=0 ? 1/_x : 0,_y!=0 ? 1/_y : 0,_z!=0 ? 1/_z : 0); }
	/// Return a vector with each component of `this' replaced with 1 if positive otherwise -1.
	vec3 sign() const { return vec3(_x>=0 ? 1 : -1,_y>=0 ? 1 : -1,_z>=0 ? 1 : -1); }
	/// Return the cross product of `this' and `v'.
	vec3 cross(const vec3& v) const { return vec3(_y * v.z() - _z * v.y(), _z * v.x() - _x * v.z(), _x * v.y() - _y * v.x()); }
	/// Return the dot product of `this' and `v'.
	real dot(const vec3& v) const { return _x*v.x()+_y*v.y()+_z*v.z(); }
	/// Return the length of `this'.
	real len() const { return sqrt(_x*_x+_y*_y+_z*_z); }
	/// Return the squared length of `this'; this is faster than len().
	real lenSq() const { return _x*_x+_y*_y+_z*_z; }
	/// Return the normalized version of `this', or a zero vector if `this' is zero-length.
	vec3 norm() const { real l=len(); return l==0.0 ? vec3() : (*this)*(1.0/l); }
	/// Return the distance from `this' to `v'.
	real distTo(const vec3 & v) const { return ((*this)-v).len(); }
	/// Return the squared distance from `this' to `v'; this is faster than dist().
	real distToSq(const vec3 & v) const { return ((*this)-v).lenSq(); }
	/// Return a vector whose components are clamped within the AABB defined by the given vectors
	vec3 clamp(const vec3& v1,const vec3& v2) const { return vec3(RenderTypes::clamp(_x,v1.x(),v2.x()),RenderTypes::clamp(_y,v1.y(),v2.y()),RenderTypes::clamp(_z,v1.z(),v2.z())); }
	
	/// Set each component of `this' to minimum of its component and the equivalent in `v'
	void setMinVals(const vec3 &v) { _x=_min(_x,v.x()); _y=_min(_y,v.y()); _z=_min(_z,v.z()); }
	/// Set each component of `this' to maximum of its component and the equivalent in `v'
	void setMaxVals(const vec3 &v) { _x=_max(_x,v.x()); _y=_max(_y,v.y()); _z=_max(_z,v.z()); }

	/// Normalizes `this', or do nothing if zero-length
	void normThis() { real l=len(); if(l>0){ _x/=l;_y/=l;_y/=l;} }

	/// Returns an equivalent vector in polar coordinates, assuming `this' was in cartesian coordinates
	vec3 toPolar() const { real l=len(); return l==0.0 ? vec3() : vec3(atan2(_y,_x),acos(_z/l),l); }

	/// Returns an equivalent vector in cylindrical coordinates, assuming `this' was in cartesian coordinates
	vec3 toCylindrical() const { return vec3(atan2(_y,_x),_z,sqrt(_y*_y+_x*_x)); }
	
	/// Returns an equivalent vector in cartesian coordinates, assuming `this' was in polar coordinates
	vec3 fromPolar() const { return vec3(cos(_x)*sin(_y)*_z,sin(_y)*sin(_x)*_z,cos(_y)*_z); }

	/// Returns an equivalent vector in cartesian coordinates, assuming `this' was in cylindrical coordinates
	vec3 fromCylindrical() const { return vec3(cos(_x)*_z,sin(_x)*_z,_y); }

	/// Returns true if the length of the vector is within dEPSILON of 0
	bool isZero() const { return equalsEpsilon(_x+_y+_z,0.0); }

	/// Returns true if the vector is within the axis-aligned bounding box defined by the given min and max corners with a 'dEPSILON' margin of error 
	bool inAABB(const vec3& minv, const vec3& maxv) const
	{
		//return (_x+dEPSILON)>=minv.x() && (_y+dEPSILON)>=minv.y() && (_z+dEPSILON)>=minv.z()
		//	&& (_x-dEPSILON)<=maxv.x() && (_y-dEPSILON)<=maxv.y() && (_z-dEPSILON)<=maxv.z();
		return *this>minv && *this<maxv;
	}

	/// Returns true if the vector is within the oriented bounding box defined by the given center position and half X/Y/Z dimension vectors
	bool inOBB(const vec3& center, const vec3& hx, const vec3& hy, const vec3& hz) const
	{
		vec3 diff=(*this)-center;

		// perform 3 plane distance checks, return true if the distance from plane (center,hx) is less than hx.len(), etc
		return fabs(hx.dot(diff))<=hx.lenSq() && fabs(hy.dot(diff))<=hy.lenSq() && fabs(hz.dot(diff))<=hz.lenSq();
	} 
	
	/// Returns true if the vector's distance to `center' is less than or equal to `radius'+`dEPSILON'
	bool inSphere(const vec3& center,real radius) const { return distToSq(center)<=(radius*radius+dEPSILON); }

	/// Returns true if the vector lies on the plane defined by the point `planept' and normal `planenorm'
	bool onPlane(const vec3& planept, const vec3& planenorm) const { return equalsEpsilon(planeDist(planept,planenorm),0); }
	
	/// Returns true if each component is on the interval [0,1]; this exact within a value of `margin' in the positive and negative directions
	bool isInUnitCube(real margin=0.0) const { return _x>=-margin && _x<=(1.0+margin) && _y>=-margin && _y<=(1.0+margin) && _z>=-margin && _z<=(1.0+margin); }

	/// Returns true if `other' is parallel with this vector, ie. they represent the same or opposite directions.
	bool isParallel(const vec3 &other) const
	{
		return cross(other).isZero();
	}

	/// Returns true if the components of `this' and `v' are within `dEPSILON' of one another
	bool operator == (const vec3 & v) const { return equalsEpsilon(_x,v.x()) && equalsEpsilon(_y,v.y()) && equalsEpsilon(_z,v.z()); }
	
	/// Equals the inverse of ==
	bool operator != (const vec3 &v) const { return !((*this)==v); }
	
	bool operator < (const vec3 &v) const { return (_x-dEPSILON)<v.x() && (_y-dEPSILON)<v.y() && (_z-dEPSILON)<v.z(); }
	bool operator > (const vec3 &v) const { return (_x+dEPSILON)>v.x() && (_y+dEPSILON)>v.y() && (_z+dEPSILON)>v.z(); }
	
	int cmp(const vec3 &v) const
	{
		// the order of these statements defines the sorting order where Z is used to sort first and X last
		if(_z<v.z()) return -1;
		if(_z>v.z()) return  1;
		if(_y<v.y()) return -1;
		if(_y>v.y()) return  1;
		if(_x<v.x()) return -1;
		if(_x>v.x()) return  1;
		return 0;
	}

	/// Returns the angle between `this' and `v'
	real angleTo(const vec3 &v) const
	{
		real l=sqrt(lenSq() * v.lenSq());

		if(l<dEPSILON)
			return 0.0;

		real vl=dot(v)/l;

		if(vl>=(1.0-dEPSILON))
			return 0.0;
		
		if(vl<=(-1.0+dEPSILON))
			return dPI;

		return acos(vl);
	}

	/// Returns the normal of a plane defined by `this', `v2', and `v3' winding clockwise
	vec3 planeNorm(const vec3& v2, const vec3& v3) const { return (v2-*this).cross(v3-*this).norm(); }
	
	/// Returns the normal of a plane defined by `this', `v2', and `v3' with `farv' defined as below the plane 
	vec3 planeNorm(const vec3& v2, const vec3& v3, const vec3& farv) const
	{
		vec3 norm=planeNorm(v2,v3);
		return norm.angleTo(farv-*this)>=(dPI*0.5) ? norm : -norm;
	}

	/// Returns the distance from `this' to a plane defined by a point on the plane and the plane normal (positive if above plane, negative below)
	real planeDist(const vec3& planept, const vec3& planenorm) const { return planenorm.dot((*this)-planept); }

	/// Returns the projection of `this' on a plane defined by a point on the plane and the plane normal
	vec3 planeProject(const vec3& planept, const vec3& planenorm) const { return (*this)-(planenorm*planeDist(planept,planenorm)); }
	
	/// Given a plane defined by this and `planenorm', returns the circular ordering of `v1' and `v2'.
	int planeOrder(const vec3& planenorm,const vec3& v1,const vec3& v2) const
	{
		real order=(v1-*this).cross(v2-*this).dot(planenorm);
		if(order>0)
			return 1;
		if(order<0)
			return -1;
		return 0;
	}

	/// Returns the area of a triangle defined by `this', `b', and `c'.
	real triArea(const vec3& b, const vec3& c) const
	{
		vec3 bb=b-*this;
		vec3 cc=c-*this;
		
		return bb.len()*cc.len()*sin(bb.angleTo(cc))*0.5;
	}

	/// Returns the cylindrical distance from `this' to the line segment `p1'->`p2', or -1 if p1==p2 or `this' isn't within a cylinder with p1->p2 as its centeline.
	real lineDist(vec3 p1,vec3 p2) const
	{
		vec3 p=p2-p1;
		real pl=p.len();
		if(pl<dEPSILON) // p1==p2 so there's no line
			return -1;

		if(planeDist(p1,p)<0 || planeDist(p2,-p)<0) // this is outside the cylinder area
			return -1;

		return p.cross(p1-*this).len()/pl;
	}
	
	/// Linearly interpolate between `this' and `v'.
	vec3 lerp(real val,const vec3& v) const
	{
		return vec3(_x+(v.x()-_x)*val,_y+(v.y()-_y)*val,_z+(v.z()-_z)*val);
	}

	i32 hash() const
	{
		union { real f; i64 i;} x,y,z;
		x.f=_x;
		y.f=_y;
		z.f=_z;
		
		i64 hash=_HASH(x.i,_HASH(y.i,z.i,13),14);
		return i32(hash>>32)^i32(hash);
	}
	
	friend std::ostream& operator << (std::ostream &out, const vec3 &v)
	{
		return out << "vec3(" << v.x() << ", " << v.y() << ", " << v.z() << ")";
	}

	static int compX(const void* v1, const void* v2)
	{
		return compT<real>(((const vec3*)v1)->x(),((const vec3*)v2)->x());
	}

	static int compY(const void* v1, const void* v2)
	{
		return compT<real>(((const vec3*)v1)->y(),((const vec3*)v2)->y());
	}

	static int compZ(const void* v1, const void* v2)
	{
		return compT<real>(((const vec3*)v1)->z(),((const vec3*)v2)->z());
	}
	
	static vec3 posInfinity() { return vec3(realInf); }
	static vec3 negInfinity() { return vec3(-realInf); }

	/// Returns the X-axis unit vector.
	static vec3 X() { return vec3(1,0,0); }

	/// Returns the Y-axis unit vector.
	static vec3 Y() { return vec3(0,1,0); }

	/// Returns the Z-axis unit vector.
	static vec3 Z() { return vec3(0,0,1); }
};

class mat4
{
public:
	union {
		struct{ 
			real 
			m00,m01,m02,m03,
			m10,m11,m12,m13,
			m20,m21,m22,m23,
			m30,m31,m32,m33;
		};
		real m[4][4];
	};

	mat4() { clear(); }
	mat4(const real* mat) { memcpy(m,mat,sizeof(real)*16); }
	mat4(real m00,real m01,real m02,real m03, real m10,real m11,real m12,real m13, real m20,real m21,real m22,real m23, real m30,real m31,real m32,real m33) : 
		m00(m00),m01(m01),m02(m02),m03(m03), m10(m10),m11(m11),m12(m12),m13(m13), m20(m20),m21(m21),m22(m22),m23(m23), m30(m30),m31(m31),m32(m32),m33(m33) {}

	void clear() { memset(m,0,sizeof(real)*16); }
	void ident() { clear(); m00=m11=m22=m33=1.0; }

	vec3 operator * (const vec3& v) const
	{
		vec3 vv= vec3(m00*v.x() + m01*v.y() + m02*v.z() + m03,m10*v.x() + m11*v.y() + m12*v.z() + m13,m20*v.x() + m21*v.y() + m22*v.z() + m23);
		real d=m30*v.x() + m31*v.y() + m32*v.z() + m33;
		return d==0 ? vec3() : (vv/d);
	}

	friend vec3 operator * (const vec3 &v,const mat4& m)
	{
		return m*v;
	}

	mat4 operator * (const mat4& m) const
	{
		return mat4(
			m.m00*m00 + m.m10*m01 + m.m20*m02 + m.m30*m03,
			m.m01*m00 + m.m11*m01 + m.m21*m02 + m.m31*m03,
			m.m02*m00 + m.m12*m01 + m.m22*m02 + m.m32*m03,
			m.m03*m00 + m.m13*m01 + m.m23*m02 + m.m33*m03,
			m.m00*m10 + m.m10*m11 + m.m20*m12 + m.m30*m13,
			m.m01*m10 + m.m11*m11 + m.m21*m12 + m.m31*m13,
			m.m02*m10 + m.m12*m11 + m.m22*m12 + m.m32*m13,
			m.m03*m10 + m.m13*m11 + m.m23*m12 + m.m33*m13,
			m.m00*m20 + m.m10*m21 + m.m20*m22 + m.m30*m23,
			m.m01*m20 + m.m11*m21 + m.m21*m22 + m.m31*m23,
			m.m02*m20 + m.m12*m21 + m.m22*m22 + m.m32*m23,
			m.m03*m20 + m.m13*m21 + m.m23*m22 + m.m33*m23,
			m.m00*m30 + m.m10*m31 + m.m20*m32 + m.m30*m33,
			m.m01*m30 + m.m11*m31 + m.m21*m32 + m.m31*m33,
			m.m02*m30 + m.m12*m31 + m.m22*m32 + m.m32*m33,
			m.m03*m30 + m.m13*m31 + m.m23*m32 + m.m33*m33
		);
	}
	
	real determinant() const
	{
		//return m00*m11*m22*m33 - m00*m11*m23*m32 - m00*m12*m21*m33 + m00*m12*m23*m31 + 
		//	m00*m13*m21*m32 - m00*m13*m22*m31 - m01*m10*m22*m33 + m01*m10*m23*m32 + 
		//	m01*m12*m20*m33 - m01*m12*m23*m30 - m01*m13*m20*m32 + m01*m13*m22*m30 + 
		//	m02*m10*m21*m33 - m02*m10*m23*m31 - m02*m11*m20*m33 + m02*m11*m23*m30 + 
		//	m02*m13*m20*m31 - m02*m13*m21*m30 - m03*m10*m21*m32 + m03*m10*m22*m31 + 
		//	m03*m11*m20*m32 - m03*m11*m22*m30 - m03*m12*m20*m31 + m03*m12*m21*m30;
		
		real x0 = m00*m11, x1 = m22*m33, x2 = m00*m12, x3 = m23*m31, x4 = m00*m13, x5 = m21*m32, x6 = m01*m10, 
			x7 = m23*m32, x8 = m01*m12, x9 = m20*m33, x10 = m01*m13, x11 = m22*m30, x12 = m02*m10, x13 = m21*m33, 
			x14 = m02*m11, x15 = m23*m30, x16 = m02*m13, x17 = m20*m31, x18 = m03*m10, x19 = m22*m31, 
			x20 = m03*m11, x21 = m20*m32, x22 = m03*m12, x23 = m21*m30;
			
		return x0*x1 - x0*x7 - x1*x6 + x10*x11 - x10*x21 - x11*x20 + x12*x13 - x12*x3 - x13*x2 + x14*x15 - x14*x9 - x15*x8 + 
			x16*x17 - x16*x23 - x17*x22 + x18*x19 - x18*x5 - x19*x4 + x2*x3 + x20*x21 + x22*x23 + x4*x5 + x6*x7 + x8*x9;
	}
	
	mat4 inverse() const
	{
		real s0 =  m00*m11 - m01*m10;
		real s1 =  m00*m12 - m02*m10;
		real s2 =  m00*m13 - m03*m10;
		real s3 =  m01*m12 - m02*m11;
		real s4 =  m01*m13 - m03*m11;
		real s5 =  m02*m13 - m03*m12;
		real c5 =  m22*m33 - m23*m32;
		real c4 =  m21*m33 - m23*m31;
		real c3 =  m21*m32 - m22*m31;
		real c2 =  m20*m33 - m23*m30;
		real c1 =  m20*m32 - m22*m30;
		real c0 =  m20*m31 - m21*m30;
		 
		real invdet = 1.0 / (s0 * c5 - s1 * c4 + s2 * c3 + s3 * c2 - s4 * c1 + s5 * c0);
		 
		real b00 = ( c3*m13 - c4*m12 + c5*m11 ) * invdet;
		real b01 = ( -c3*m03 + c4*m02 - c5*m01 ) * invdet;
		real b02 = ( m31*s5 - m32*s4 + m33*s3 ) * invdet;
		real b03 = ( -m21*s5 + m22*s4 - m23*s3 ) * invdet;
		real b10 = ( -c1*m13 + c2*m12 - c5*m10 ) * invdet;
		real b11 = ( c1*m03 - c2*m02 + c5*m00 ) * invdet;
		real b12 = ( -m30*s5 + m32*s2 - m33*s1 ) * invdet;
		real b13 = ( m20*s5 - m22*s2 + m23*s1 ) * invdet;
		real b20 = ( c0*m13 - c2*m11 + c4*m10 ) * invdet;
		real b21 = ( -c0*m03 + c2*m01 - c4*m00 ) * invdet;
		real b22 = ( m30*s4 - m31*s2 + m33*s0 ) * invdet;
		real b23 = ( -m20*s4 + m21*s2 - m23*s0 ) * invdet;
		real b30 = ( -c0*m12 + c1*m11 - c3*m10 ) * invdet;
		real b31 = ( c0*m02 - c1*m01 + c3*m00 ) * invdet;
		real b32 = ( -m30*s3 + m31*s1 - m32*s0 ) * invdet;
		real b33 = ( m20*s3 - m21*s1 + m22*s0 ) * invdet;
	
		return mat4(b00,b01,b02,b03,b10,b11,b12,b13,b20,b21,b22,b23,b30,b31,b32,b33);
	}
};

/**
 * Quaternion rotator (see http://3dengine.org/Quaternions, http://www.cprogramming.com/tutorial/3d/quaternions.html)
 * 
 * Quaternions represent abitrary affine rotations, usually described as rotations about an given axis vector. The advantage
 * over matrices for rotations is fewer floating point calculations and avoidance of gimbal lock. Note the lack of virtual 
 * members implies no vtable pointer.
 */
class rotator
{
protected:
	real _w,_x,_y,_z;

public:
	/// Default no-op
	rotator() : _w(1),_x(0),_y(0),_z(0)
	{}

	/// Copy constructor
	rotator(const rotator &r)
	{
		set(r);
	}

	/// Defines a rotation about the given axis.
	rotator(const vec3& axis, real rads)
	{
		setAxis(axis,rads);
	}

		
	/// Defines a rotator by the given quaternion values.
	rotator(real x, real y, real z, real w)
	{
		set(x,y,z,w);
	}
	
	/// Defines the rotation which transforms normalized vectors `from' to `to' rotating about their cross product.
	rotator(const vec3& from, const vec3& to)
	{
		if(from==to)
			set(0,0,0,1);
		//else if(from.isParallel(to)){
		//	vec3 axis=from.isParallel(vec3(1,0,0)) ? vec3(0,1,0) : vec3(1,0,0);
		//	setAxis(axis.cross(from),dPI);
		//}
		else
			setAxis(from.cross(to),from.angleTo(to));
	}

	/// Defines a rotation from Euler angles: yaw = Z-axis rotation, pitch = X-axis rotation, roll = Y-axis rotation.
	rotator(real yaw, real pitch, real roll)
	{
		real c1 = cos(0.5*roll); // was yaw in the original (X=right, Y=up, Z=towards) axes definition
		real s1 = sin(0.5*roll);
		real c2 = cos(0.5*yaw); // was pitch
		real s2 = sin(0.5*yaw);
		real c3 = cos(0.5*pitch); // was roll
		real s3 = sin(0.5*pitch);
		real c1c2 = c1*c2;
		real s1s2 = s1*s2;
		real c1s2 = c1*s2;
		real s1c2 = s1*c2;
                
		_w =c1c2*c3 - s1s2*s3;
		_x =c1c2*s3 + s1s2*c3;
		_y =s1c2*c3 + c1s2*s3;
		_z =c1s2*c3 - s1c2*s3;

		// TODO: the above defines ordering of rotations as pitch-yaw-roll, is this correct? This instead perhaps:
		//set(rotator(vec3::Z(),yaw)*rotator(vec3::X(),pitch)*rotator(vec3::Y(),roll));
	}
	
	/// Defines a rotation from the significant 3x3 components of a 4x4 rotation matrix
	rotator(real m00,real m01,real m02,real m10,real m11,real m12,real m20,real m21,real m22)
	{
		real tr = m00 + m11 + m22;
		
		if (tr > 0) { 
			real S = sqrt(tr+1.0) * 2; // S=4*qw 
			_w = 0.25 * S;
			_x = (m21 - m12) / S;
			_y = (m02 - m20) / S; 
			_z = (m10 - m01) / S; 
		} else if(m00 > m11 && m00 > m22) { 
			real S = sqrt(1.0 + m00 - m11 - m22) * 2; // S=4*qx 
			_w = (m21 - m12) / S;
			_x = 0.25 * S;
			_y = (m01 + m10) / S; 
			_z = (m02 + m20) / S; 
		} else if (m11 > m22) { 
			real S = sqrt(1.0 + m11 - m00 - m22) * 2; // S=4*qy
			_w = (m02 - m20) / S;
			_x = (m01 + m10) / S; 
			_y = 0.25 * S;
			_z = (m12 + m21) / S; 
		} else { 
			real S = sqrt(1.0 + m22 - m00 - m11) * 2; // S=4*qz
			_w = (m10 - m01) / S;
			_x = (m02 + m20) / S;
			_y = (m12 + m21) / S;
			_z = 0.25 * S;
		}
	}
	
	/**
	 * Defines a rotation to transform a plane defined with row/column vectors (row2,col2) to plane (row1,col1). 
	 * 
	 * This implies a rotation between plane normals and a rotation to transform the 
	 * right-facing vector to the row vector. All args are assumed normalized.
	 */
	rotator(vec3 row1, vec3 col1, vec3 row2, vec3 col2)
	{
		vec3 norm1=col1.cross(row1).norm(); // first plane normal
		vec3 norm2=col2.cross(row2).norm(); // second plane normal                
		rotator rot;
		
		// define rot as the rotation aligning the second plane to the first
		if(norm1==-norm2)
			rot=rotator(row1,dPI); // flip along the row vector
		else
			rot=rotator(norm2,norm1);
                
		// combine rot with a rotation which aligns row vectors by rotating in the first plane, then assign values to this object
		//set(rotator(norm1,row1.angleTo(rot*row2))*rot); // y u no work?
		set(rotator(rot*row2,row1)*rot);
	}

	/// Set the rotator to represent a rotation of `rads' radians around `axis'
	void setAxis(const vec3& axis, real rads)
	{
		if(!equalsEpsilon(rads,0.0) && !axis.isZero()){
			vec3 na=axis.norm();
			real srads = (real)sin(rads / 2.0);
			set(na.x()*srads,na.y()*srads,na.z()*srads,(real)cos(rads / 2.0));
		}
		else
			set(0,0,0,1);
	}
	
	/// Copy the values of `r' into `this'
	void set(const rotator& r)
	{
		set(r._x,r._y,r._z,r._w);
	}

	/// sets parameters given the normalized quaternion components
	void set(real ry,real rz, real rw)
	{
		set(sqrt(1.0-(ry*ry+rz*rz+rw*rw)),ry,rz,rw);
	}

	/// Sets all parameters to those provided
	void set(real rx,real ry, real rz,real rw)
	{
		_x = rx;
		_y = ry;
		_z = rz;
		_w = rw;
	}

	real w() const { return _w; }
	real x() const { return _x; }
	real y() const { return _y; }
	real z() const { return _z; }

	/// Get the pitch angle (x-axis rotation in radians)
	real getPitch() const
	{
		real test=_x*_y+_z*_w;
		if(test>(0.5-dEPSILON))
			return 0;
		
		if(test<(-0.5+dEPSILON))
			return 0;
		
		return atan2(2*_x*_w-2*_y*_z , 1 - 2*_x*_x - 2*_z*_z);
	}

	/// Get the yaw angle (z-axis rotation in radians)
	real getYaw() const
	{	
		real test=_x*_y+_z*_w;
		if(test>(0.5-dEPSILON))
			return dPI*0.5;
		
		if(test<(-0.5+dEPSILON))
			return dPI*-0.5;
		
		return asin(2*test); 
	}

	/// Get the roll angle (y-axis rotation in radians)
	real getRoll() const
	{
		real test=_x*_y+_z*_w;
		if(test>(0.5-dEPSILON))
			return 2*atan2(_x,_w);
		
		if(test<(-0.5+dEPSILON))
			return -2*atan2(_x,_w);
		
		return atan2(2*_y*_w-2*_x*_z , 1 - 2*_y*_y - 2*_z*_z);
	}

	/// Rotate `v' according to this rotator's parameters
	vec3 operator * (const vec3 &v) const
	{
		vec3 axis(_x,_y,_z);
		vec3 vc=axis.cross(v);
		vec3 vcc=axis.cross(vc);
		return (vc*(2.0*_w))+(vcc*2.0)+v;
	}
	
	/// Commutative version of the above
	friend vec3 operator * (const vec3 &v,const rotator& r)
	{
		return r*v;
	}

	vec3 operator / (const vec3& v) const
	{
		return inverse()*v;
	}

	/// Commutative version of the above
	friend vec3 operator / (const vec3 &v,const rotator& r)
	{
		return r/v;
	}

	/// Returns a rotator representing the rotation `r' followed by `this'
	rotator operator * (const rotator & r) const
	{
		rotator rr;
		rr.set( _w * r._x + _x * r._w + _y * r._z - _z * r._y,
			_w * r._y + _y * r._w + _z * r._x - _x * r._z,
			_w * r._z + _z * r._w + _x * r._y - _y * r._x,
			_w * r._w - _x * r._x - _y * r._y - _z * r._z);
		return rr;
	}
	
	rotator operator * (real r) const 
	{
		rotator rr;
		rr.set(_x*r,_y*r,_z*r,_w*r);
		return rr;
	}

	rotator operator + (const rotator & r) const
	{
		rotator rr;
		rr.set(_x+r._x,_y+r._y,_z+r._z,_w+r._w);
		return rr;
	}
	
	rotator operator - (const rotator & r) const
	{
		rotator rr;
		rr.set(_x-r._x,_y-r._y,_z-r._z,_w-r._w);
		return rr;
	}
	
	rotator operator - () const
	{
		rotator rr;
		rr.set(-_x,-_y,-_z,-_w);
		return rr;
	}

	bool operator == (const rotator & v) const
	{
		if(equalsEpsilon(_w,v._w) && equalsEpsilon(_x,v._x) && equalsEpsilon(_y,v._y) && equalsEpsilon(_z,v._z))
			return true;

		if(equalsEpsilon(-_w,v._w) && equalsEpsilon(-_x,v._x) && equalsEpsilon(-_y,v._y) && equalsEpsilon(-_z,v._z))
			return true;

		return false;
	}
	
	bool operator != (const rotator &v) const { return !((*this)==v); }

	rotator conjugate() const
	{
		rotator rr;
		rr.set(-_x,-_y,-_z,_w);
		return rr;
	}

	real len() const
	{
		return sqrt(_x*_x+_y*_y+_z*_z+_w*_w);
	}
	
	real dot(const rotator &r) const
	{
		return _x*r._x + _y*r._y + _z*r._z + _w*r._w;
	}

	rotator norm() const
	{
		rotator rr(*this);
		rr.normThis();
		return rr;
	}

	void normThis()
	{
		real n=len();
		if(n!=0.0){
			_x/=n;
			_y/=n;
			_z/=n;
			_w/=n;
		}
	}

	/// Returns a rotator representing the opposite rotation
	rotator inverse() const
	{
		rotator rr=conjugate();
		rr.normThis();
		return rr;
	}
	
	/// Semi-linearly interpolates between `this' and `r', this varies from a circular interpolation but is faster
	rotator interpolate(real val,const rotator& r) const
	{
		if(val>=1)
			return r;

		if(val<=0)
			return *this;

		rotator rr;
		rr.set(*this + ((dot(r)<0.0 ? -r : r) - *this)*val);
		rr.normThis();
		
		return rr;
	}

	void toMatrix(real* mat) const
	{
		rotator r=this->norm();
		real x2=r.x()*r.x(),y2=r.y()*r.y(),z2=r.z()*r.z(),
			 xy=r.x()*r.y(),xz=r.x()*r.z(),yz=r.y()*r.z(),
			 wz=r.w()*r.z(),wx=r.w()*r.x(),wy=r.w()*r.y();

		mat[ 0] = 1.0f - 2.0f * ( y2 + z2 ); 
		mat[ 1] = 2.0f * (xy - wz);
		mat[ 2] = 2.0f * (xz + wy);
		mat[ 3] = 0.0f;  
		mat[ 4] = 2.0f * (xy + wz);  
		mat[ 5] = 1.0f - 2.0f * (x2 + z2); 
		mat[ 6] = 2.0f * (yz - wx );  
		mat[ 7] = 0.0f;  
		mat[ 8] = 2.0f * (xz - wy);
		mat[ 9] = 2.0f * (yz + wx);
		mat[10] = 1.0f - 2.0f * (x2 + y2);  
		mat[11] = 0.0f;  
		mat[12] = 0;  
		mat[13] = 0;  
		mat[14] = 0;  
		mat[15] = 1.0f;
	}

	mat4 toMatrix() const
	{
		mat4 m;
		toMatrix((real*)m.m);
		return m;
	}

	i32 hash() const
	{
		union { real f; i64 i;} x,y,z,w;
		x.f=_x;
		y.f=_y;
		z.f=_z;
		w.f=_w;
		
		i64 hash=_HASH(x.i,_HASH(y.i,_HASH(z.i,w.i,12),13),14);
		return i32(hash>>32)^i32(hash);
	}
	
	friend std::ostream& operator << (std::ostream &out,const rotator &r)
	{
		return out << "rotator(" << r.x() << ", " << r.y() << ", " << r.z() << ", " << r.w() << ")";
	}
};

/*****************************************************************************************************************************/
/* Exceptions */
/*****************************************************************************************************************************/

class IndexException : public std::exception
{
protected:
	std::string name;
	std::string msg;
	size_t val, maxval;

	void setMsg()
	{
		std::ostringstream out;
		out << "Bad value " << val << " for index '" << name.c_str() << "' (0 <= " << name.c_str() << " < " << maxval << ")";
		msg=out.str();
	}

public:
	IndexException(std::string name, size_t val, size_t maxval) : name(name),val(val),maxval(maxval)
	{
		setMsg();
	}

	IndexException(const IndexException& ind) : name(ind.name),val(ind.val),maxval(ind.maxval)
	{
		setMsg();
	}

	virtual ~IndexException() throw() {}

	virtual const char* what() const throw() { return msg.c_str(); }
};

class MemException : public std::exception
{
protected:
	std::string msg;
public:
	MemException(const std::string msg) : msg(msg){}

	MemException(const std::string m,int err)
	{
		std::ostringstream out;
		out << m << ": errno: " << strerror(errno);
		msg=out.str();
	}

	MemException(const MemException & op) : msg(op.msg) {}

	virtual ~MemException() throw() {}

	virtual const char* what() const throw() { return msg.c_str(); }
};

class RenderException : public std::exception
{
protected:
	std::string msg;
public:
	RenderException(const std::string msg) : msg(msg){}

	RenderException(const std::string msg, const char* file, int line){
		std::ostringstream out;
		out << file << ":" << line << ":" << msg;
		this->msg=out.str();
	}

	RenderException(const RenderException & op) : msg(op.msg) {}

	virtual ~RenderException() throw() {}

	virtual const char* what() const throw() { return msg.c_str(); }
};

class ValueException : public std::exception
{
protected:
	std::string msg;
public:
	ValueException(const std::string valuename, const std::string msg, const char* file=NULL, int line=-1) 
	{
		std::ostringstream out;
		if(file)
			out << file << ":" << line << ": ";
		out << "Bad value for " << valuename  << ": " << msg;
		this->msg=out.str();

	}

	ValueException(const ValueException & op) : msg(op.msg) {}

	virtual ~ValueException() throw() {}

	virtual const char* what() const throw() { return msg.c_str(); }
};

inline void checkNull(const std::string valuename, const void* val, const char* file=NULL, int line=-1) throw(ValueException)
{
	if(val==NULL)
		throw ValueException(valuename,"Must not be null",file,line);
}

#define CHECK_NULL(val) checkNull("val",(const void*)val,__FILE__,__LINE__)

/*****************************************************************************************************************************/
/* Data Structure Objects */
/*****************************************************************************************************************************/

/// Using mmap, copy the contents from file `filename' into `dest' starting `offset' bytes from the beginning
void readBinaryFileToBuff(const char* filename,size_t offset,void* dest,size_t len) throw(MemException);

/// Using mmap, copy the contents of `header' and then `src' into file `filename'
void storeBufftoBinaryFile(const char* filename,void* src,size_t len,int* header, size_t headerlen) throw(MemException);

/// This base type provides facilities for maintaining name-value metadata pairs
class MetaType
{
protected:
	//typedef std::pair<std::string,std::string> strpair;
	typedef std::map<std::string,std::string> metamap;
	typedef metamap::iterator iter;
	typedef metamap::const_iterator citer;

	metamap _meta;
public:
	
	/// Returns true if a key-value pair with the given key is present 
	bool hasMetaKey(const char* key) const { return _meta.find(key)!=_meta.end(); }

	std::vector<std::string> getMetaKeys() const
	{
		std::vector<std::string> result;
		for(citer i=_meta.begin();i!=_meta.end();i++)
			result.push_back((*i).first);

		return result;
	}

	std::string meta() const
	{
		std::ostringstream out;
		for(citer c=_meta.begin();c!=_meta.end();c++)
			out << (*c).first << " = " << (*c).second << std::endl;

		return out.str();
	}

	/// Returns the value associated with the given key or the empty string if none is stored
	const char* meta(const char* key) const
	{
		return hasMetaKey(key) ? _meta.find(key)->second.c_str() : "";
	}

	/// Add the given key-value pair to the metadata, or overwrite an existing if present. Does nothing if either argument is NULL.
	void meta(const char* key, const char* val)
	{
		if(!key || !val)
			return;
		
		std::string fkey=key,fval=val;
		
		// filter out | characters
		fkey.erase (std::remove(fkey.begin(), fkey.end(), '|'), fkey.end());
		fval.erase (std::remove(fval.begin(), fval.end(), '|'), fval.end());

		_meta[fkey]=fval;
	}
	
	/// Copy all the metadata from `m' to `this'
	void meta(const MetaType* m)
	{
		for(citer i=m->_meta.begin();i!=m->_meta.end();i++)
			meta((*i).first.c_str(),(*i).second.c_str());
	}
	
	/// Turn all metadata name-value pairs into one string suitable for pickling
	std::string serializeMeta() const
	{
		std::ostringstream out;
		for(citer i=_meta.begin();i!=_meta.end();i++)
			out << (*i).first << "||" << (*i).second << "||";
		
		return out.str();
	}
	
	/// Break a string generated by the above back into name-value pairs and store in `this'
	void deserializeMeta(const std::string &s)
	{
		char *buf=new char[s.length()+1];
		strcpy(buf,s.c_str());
		
		char* p=strtok(buf,"|");
		
		while(p!=NULL){
			std::string key=p;
			p=strtok(NULL,"|");
			std::string val=p;
			_meta[key]=val;
			p=strtok(NULL,"|");
		}
		
		delete buf;
	}
};

// Metaprogramming types encapsulating the 4 operators +-/*
template<typename R,typename LH, typename RH> struct AddOp { static inline R op(const LH& lh, const RH& rh) { return lh+rh; } };
template<typename R,typename LH, typename RH> struct SubOp { static inline R op(const LH& lh, const RH& rh) { return lh-rh; } };
template<typename R,typename LH, typename RH> struct DivOp { static inline R op(const LH& lh, const RH& rh) { return lh/rh; } };
template<typename R,typename LH, typename RH> struct MulOp { static inline R op(const LH& lh, const RH& rh) { return lh*rh; } };


// Metaprogramming types for encapsulating the endian swap functions
template<typename T> struct SwapEndian { static T swap(T t) { return swapEndianN(t); } };
template<> struct SwapEndian<real> { static real swap(real t) { return swapEndian64(t); } };
template<> struct SwapEndian<indexval> { static indexval swap(indexval t) { return swapEndian32(t); } };
template<> struct SwapEndian<vec3> { static vec3 swap(vec3 t) { return vec3(swapEndian64(t.x()),swapEndian64(t.y()),swapEndian64(t.z())); } };
template<> struct SwapEndian<color> { static color swap(color t) { return color(swapEndian32(t.r()),swapEndian32(t.g()),swapEndian32(t.b()),swapEndian32(t.a())); } };

/** 
 * This represents a 2-dimensional array of data elements of type T. There are four typedefs given below for T being
 * vec3, color, indexval, and real. A number of methods are provided for doing arithmetic with all the elements of a
 * matrix and with whole matrices. A facility is provided for defining matrices as shared memory segments suitable for
 * communication between processes. 
 */
template<typename T> class Matrix : public MetaType
{
protected:
	std::string _name; // matrix name, should be unique application-wide
	std::string _type; // type of matrix, may be an empty string if types don't make sense for what's stored
	std::string _sharedname; // name of the share memory segment `data' refers to

	T* data; // refers to locally-allocated segments of mmap-addressed shared memory segments
	sval _n_actual; // actual length of allocated data, >=_n
	sval _n,_m; // _n rows, _m columns

	bool _isShared; // true if the memory is shared, false if locally allocated memory
	
#ifdef WIN32
	HANDLE mapFile;
#endif

public:
	
	/// Constructs a matrix named `name' of `n' rows and `m' columns, local if `isShared' is false and shared otherwise
	Matrix(const char* name,sval n, sval m=1,bool isShared=false)  throw(MemException) :
			_name(name), _type(""),_sharedname(""),data(0),_n_actual(0),_n(n),_m(m),_isShared(false)
	{
		setShared(isShared);
	}

	/// Constructs a matrix named `name' with type `type' of `n' rows and `m' columns, local if `isShared' is false and shared otherwise
	Matrix(const char* name,const char* type,sval n, sval m=1,bool isShared=false)  throw(MemException) :
			_name(name), _type(type),_sharedname(""),data(0),_n_actual(0),_n(n),_m(m),_isShared(false)
	{
		setShared(isShared);
	}

	/// Constructor for unpickling only, do not use
	Matrix(const char* name,const char* type,const char* sharedname,const char* serialmeta,sval n, sval m) throw(MemException)  :
			_name(name), _type(type),_sharedname(sharedname),data(0),_n_actual(n),_n(n),_m(m),_isShared(true)
	{
		deserializeMeta(serialmeta);
		data=createShared();
	}

	/// Constructor for converting a memory pointer into a Matrix, this will copy n*m values from `array'.
	Matrix(const char* name,const char* type,const T* array,sval n, sval m,bool isShared=false)  throw(MemException) :
		_name(name), _type(type),_sharedname(""),data(0),_n_actual(0),_n(n),_m(m),_isShared(false)
	{
		setShared(isShared);
		memcpy(data,array,memSize());
	}

	virtual ~Matrix()
	{
		clear();
	}

	T* dataPtr() const { return data; }

	/// Copy the contents of this matrix into a newly allocated one (which can be shared if isShared is true), using `newname' if not NULL and getName() otherwise
	Matrix<T>* clone(const char* newname=NULL, bool isShared=false) const
	{
		Matrix<T>* m=new Matrix<T>(newname ? newname : _name.c_str(),_type.c_str(),_n,_m,isShared);
		memcpy(m->data,data,memSize());
		m->meta(this);
		return m;
	}

	const char* getName() const { return _name.c_str(); }
	const char* getSharedName() const { return _sharedname.c_str(); }
	const char* getType() const { return _type.c_str(); }

	void setName(const char* name) { _name=name; }
	void setType(const char* type) { _type=type; }

	/// Returns true if the matrix is allocated in shared memory
	bool isShared() const { return _isShared; }

	/**
	 * Toggles whether this matrix is in local memory or shared. If this matrix is local and the
	 * given argument is true, then a new shared segment is created, the data is copied into it, and
	 * the local segment is deallocated. If the matrix is shared and the argument false, a new local
	 * segment is allocated. The shared segment is then released and, if this matrix is the creator of
	 * the segment, it removes it from the system. If the argument is the same as the shared status, 
	 * nothing is done.
	 */
	void setShared(bool val) throw(MemException)
	{
		if(data && val==_isShared) // do nothing if the shared state to set is the current state and the matrix is allocated
			return;

		if(val){
			sval size=memSize();

			if(size==0)
				throw MemException("Cannot make empty matrix shared");

			_n_actual=_n;
			T* shared=createShared();

			if(data){
				memcpy(shared,data,size);
				delete[] data;
			}
			else
				memset(shared,0,size);

			data=shared;
		}
		else{
			T* olddata=data;
			resize();
			closeShared(olddata);
		}

		_isShared=val;
	}

	void clear() throw(MemException)
	{
		if(data){
			if(_isShared){
				closeShared(data);
				unlinkShared(_sharedname);
			}
			else if(data!=NULL)
				delete[] data;
		}

		_n_actual=0;
		_n=0;
		_isShared=false;
		data=NULL;
	}

	/// Get the number of rows
	sval n() const { return _n; }
	
	/// Get the number of columns
	sval m() const { return _m; }

	/// Get the total memory usage in bytes
	sval memSize() const { return sval(sizeof(T)*_n*_m); }

	/// Set every cell of the matrix to the given value
	void fill(const T& t)
	{
		T* d=data;
		for(sval n=0;n<_n*_m;n++)
			*d++=t;
	}

	/// Copy the data bitwise from `r', the number of bytes copied is the minimum or either matrices' size
	template<typename R> void copyFrom(const Matrix<R>* r)
	{
		sval minsize=_min(memSize(),r->memSize());
		if(minsize>0)
			memcpy(data,r->dataPtr(),minsize);
	}

	/// Create a submatrix from this one of dimensions (n,m), starting at row `noff' and column `moff'
	Matrix<T>* subMatrix(const char* name,sval n, sval m=1,sval noff=0,sval moff=0,bool isShared=false) const throw(MemException)
	{
		if(n>_n || m>_m)
			throw MemException("Submatrix dimensions may not exceed matrix dimensions");

		if((n+noff)>_n || (m+moff)>_m)
			throw MemException("Submatrix dimensions plus offsets may not exceed matrix dimensions");

		Matrix<T>* mat=new Matrix<T>(name,_type.c_str(),n,m,isShared);

		for(sval nn=0;nn<n;nn++)
			for(sval mm=0;mm<m;mm++)
				mat->at(nn,mm)=at(nn+noff,mm+moff);

		return mat;
	}

	Matrix<T>* reshape(const char* name,sval n, sval m,bool isShared=false) const throw(MemException)
	{
		Matrix<T>* mat=new Matrix<T>(name,_type.c_str(),n,m,isShared);
		memcpy(mat->dataPtr(),data,_min(mat->memSize(),memSize()));
		return mat;
	}
	
	// These methods define mathematical operators for single value or matrix right hand sides
	
	/// Apply the function `op' to each cell from (minrow,mincol) to (maxrow-1,maxcol-1), passing in `ctx' as the first argument for each call
	template<typename Ctx>
	void applyFunc(T (*op)(Ctx,const T&,sval,sval),Ctx ctx,sval minrow=0,sval mincol=0,sval maxrow=-1,sval maxcol=-1)
	{
		maxcol=_min(_m,maxcol);
		maxrow=_min(_n,maxrow);
		
		for(sval n=minrow;n<maxrow;n++)
			for(sval m=mincol;m<maxcol;m++)
				at(n,m)=op(ctx,at(n,m),n,m);
	}
	
	/// Apply the operation OpType::op to every cell from (minrow,mincol) to (maxrow-1,maxcol-1) in the matrix with `r' as the second operand
	template<typename R, typename OpType>
	void scalarop(const R& r,sval minrow=0,sval mincol=0,sval maxrow=-1,sval maxcol=-1)
	{
		maxcol=_min(_m,maxcol);
		maxrow=_min(_n,maxrow);
		
		for(sval n=minrow;n<maxrow;n++)
			for(sval m=mincol;m<maxcol;m++)
				at(n,m)=OpType::op(at(n,m),r);
	}

	/// Apply the operation OpType::op to every cell from (minrow,mincol) to (maxrow-1,maxcol-1) in the matrix with the equivalent cell in `mat' as the second operand
	template<typename R, typename OpType>
	void matop(const Matrix<R>& mat,sval minrow=0,sval mincol=0,sval maxrow=-1,sval maxcol=-1)
	{
		maxcol=_min(_min(mat.m(),_m),maxcol);
		maxrow=_min(_min(mat.n(),_n),maxrow);
		
		for(sval n=minrow;n<maxrow;n++)
			for(sval m=mincol;m<maxcol;m++)
				at(n,m)=OpType::op(at(n,m),mat(n,m));
	}
	
	/// Add `r' to every cell from (minrow,mincol) to (maxrow-1,maxcol-1) in the matrix
	template<typename R> void add(const R& r,sval minrow=0,sval mincol=0,sval maxrow=-1,sval maxcol=-1)
	{
		return scalarop<R,AddOp<T,T,R> >(r,minrow,mincol,maxrow,maxcol);
	}

	/// Subtract `r' from every cell from (minrow,mincol) to (maxrow-1,maxcol-1) in the matrix
	template<typename R> void sub(const R& r,sval minrow=0,sval mincol=0,sval maxrow=-1,sval maxcol=-1)
	{
		return scalarop<R,SubOp<T,T,R> >(r,minrow,mincol,maxrow,maxcol);
	}

	/// Multiple every cell from (minrow,mincol) to (maxrow-1,maxcol-1) in the matrix by `r'
	template<typename R> void mul(const R& r,sval minrow=0,sval mincol=0,sval maxrow=-1,sval maxcol=-1)
	{
		return scalarop<R,MulOp<T,T,R> >(r,minrow,mincol,maxrow,maxcol);
	}

	/// Divide every cell from (minrow,mincol) to (maxrow-1,maxcol-1) in the matrix by `r'
	template<typename R> void div(const R& r,sval minrow=0,sval mincol=0,sval maxrow=-1,sval maxcol=-1)
	{
		return scalarop<R,DivOp<T,T,R> >(r,minrow,mincol,maxrow,maxcol);
	}
	
	/// Add every cell from (minrow,mincol) to (maxrow-1,maxcol-1) in `mat' to the same cell in the matrix
	template<typename R> void addm(const Matrix<R>& mat,sval minrow=0,sval mincol=0,sval maxrow=-1,sval maxcol=-1)
	{
		return matop<R,AddOp<T,T,R> >(mat,minrow,mincol,maxrow,maxcol);
	}
	
	/// Subtract every cell from (minrow,mincol) to (maxrow-1,maxcol-1) in `mat' from the same cell in the matrix
	template<typename R> void subm(const Matrix<R>& mat,sval minrow=0,sval mincol=0,sval maxrow=-1,sval maxcol=-1)
	{
		return matop<R,SubOp<T,T,R> >(mat,minrow,mincol,maxrow,maxcol);
	}
	
	/// Multiply every cell from (minrow,mincol) to (maxrow-1,maxcol-1) in the matrix by the same in `mat'
	template<typename R> void mulm(const Matrix<R>& mat,sval minrow=0,sval mincol=0,sval maxrow=-1,sval maxcol=-1)
	{
		return matop<R,MulOp<T,T,R> >(mat,minrow,mincol,maxrow,maxcol);
	}
	
	/// Divide every cell from (minrow,mincol) to (maxrow-1,maxcol-1) in the matrix by the same in `mat'
	template<typename R> void divm(const Matrix<R>& mat,sval minrow=0,sval mincol=0,sval maxrow=-1,sval maxcol=-1)
	{
		return matop<R,DivOp<T,T,R> >(mat,minrow,mincol,maxrow,maxcol);
	}

	void reorderColumns(const sval *orderinds) throw(IndexException)
	{
		T* buff=new T[_m];

		for(sval j=0;j<_m;j++)
			checkIndex("sortinds",orderinds[j],_m);

		for(sval i=0;i<_n;i++){
			for(sval j=0;j<_m;j++)
				buff[j]=at(i,j);

			for(sval j=0;j<_m;j++)
				at(i,j)=buff[orderinds[j]];
		}

		delete buff;
	}

	void swapEndian()
	{
		sval len=_n*_m;
		for(sval i=0;i<len;i++)
			data[i]=SwapEndian<T>::swap(data[i]);
	}

	/// Same as getAt except returning a reference and no bounds check
	T& at(sval n, sval m=0) const { return data[m+(_m*n)]; }
	const T& atc(sval n, sval m=0) const { return data[m+(_m*n)]; }
	void ats(sval n, sval m, const T& t) { data[m+(_m*n)]=t; }
	
	/// Same as getAt except returning a reference and no bounds check
	T& operator () (sval n, sval m=0) const { return data[m+(_m*n)]; }
	
	T& operator [] (sval n) const { return data[n]; }

	/// Get the element at (n,m) in the matrix, throws exception if `n' or `m' out of range
	T getAt(sval n, sval m=0) const throw(IndexException) { return data[getIndex(n,m)]; }

	/// Set the value at (n,m) to t
	void setAt(const T& t, sval n, sval m=0) throw(IndexException) { data[getIndex(n,m)]=t; }

	/// Resize the matrix to have _newn rows, throws exception if shared
	void setN(sval _newn) throw(MemException) { checkNotShared(); _n=_newn; resize(); }

	/// Reshape to fit this many columns, does not allocate new columns but re-arranges existing ones and truncates the last row if necessary
	void setM(sval _newm) throw(MemException)
	{
		checkNotShared();
		_newm=_max<sval>(1,_newm);
		if(_newm>(_m*_n))
			throw MemException("New m value larger than matrix size");

		_n=sval((_n*_m)/_newm);
		_m=_newm;
	}

	/// Add `num' rows, throws exception if shared
	void addRows(sval num) throw(MemException) { setN(_n+num); }

	/// Ensure that at least `num' rows are reserved in memory, throws exception if shared
	void reserveRows(sval num) throw(MemException) { checkNotShared(); resize(num); }

	/// Append `t' to the bottom of `this', throws exception if shared or if columns of `t' and `this' don't match
	void append(const Matrix<T> &t) throw(MemException)
	{
		if(t.m()!=_m)
			throw MemException("Column dimensions of `this' and `t' do not match");
		
		sval oldn=_n;
		addRows(t.n());
		memcpy(data+(_m*oldn),t.data,t.memSize());
	}

	/// Append `t' to a new row, placing it in column `m'
	void append(const T& t,sval m=0) throw(MemException)
	{
		addRows(1);
		at(_n-1,m)=t;
	}

	void removeRow(sval n) throw(MemException,IndexException)
	{
		checkNotShared();
		checkIndex("n",n,_n);

		if(n<(_n-1))
			std::memmove(&data[n*_m],&data[(n+1)*_m],(_n-n-1)*_m*sizeof(T));

		setN(_n-1);
	}

	/// Read a binary file of data into this matrix starting from byte `offset'
	void readBinaryFile(const char* filename,size_t offset) throw(MemException)
	{
		readBinaryFileToBuff(filename,offset,data,memSize());
	}

	/// Read a text file of data into this matrix which has with `numHeaders' values in the header line
	void readTextFile(const char* filename,sval numHeaders) throw(MemException)
	{
		setN(0);
		readTextFileMatrix(filename,numHeaders,this);
	}
	
	/// Store the header values `header' and then this matrix's contents to the file
	void storeBinaryFile(const char* filename, int* header, sval headerlen) throw(MemException)
	{
		storeBufftoBinaryFile(filename,data,memSize(),header,headerlen);
	}

	/// Find the row-column pair in the matrix where `t' is found, or indexpair(n(),0) if not found (None in Python)
	indexpair indexOf(const T& t,sval aftern=0,sval afterm=0) const
	{
		sval numelems=_n*_m;
		sval nm=afterm+aftern*_m;

		while(nm<numelems && data[nm]!=t)
			nm++;

		return indexpair(nm/_m,nm%_m);
	}

protected:
	
	/// Get the index corresponding to cell (n,m)
	inline sval getIndex(sval n, sval m) const throw(IndexException)
	{
		checkIndex("n",n,_n);
		checkIndex("m",m,_m);

		return m+(_m*n);
	}

	inline void checkIndex(const char* name, sval val, sval maxval) const throw(IndexException)
	{
		if(val>=maxval)
			throw IndexException(name,val,maxval);
	}

	void checkNotShared() const throw(MemException)
	{
		if(_isShared)
			throw MemException("Operation may only be performed on non-shared matrices");
	}

	/** 
	 * Resize the allocated segment, or do nothing if shared or if _n+reservedNum is less than what is already allocated.
	 * To allocate a bigger segment, set _n to be what one wants, then call this method which allocates max(1000,(_n*1.5)+reserveNum)
	 * rows, copying over existing data as needed. When a matrix is first instantiated its buffer is exactly the size it 
	 * needs to be, but whenever new rows are added with setN(), reserveRows(), or append(), the _n member is set to the
	 * needed size and this method is called. 
	 */
	void resize(sval reserveNum=0)
	{
		if((_n+reserveNum)<=_n_actual && !_isShared) // do nothing if we have enough rows to meet demand and we're not shared
			return;

		// arbitrary min allocation of 1000 rows and 50% reserve, or just _n if this is the first allocation
		sval new_n_actual=data==NULL ? _n : _max<sval>(1000ul,((_n*3)/2)+reserveNum);

		if(new_n_actual<_n_actual && !_isShared)
			return;

		T* olddata=data;
		data=new T[new_n_actual*_m];

		memset(data,0,new_n_actual*_m*sizeof(T)); // always do this to ensure rows past _n_actual are clean

		if(olddata){
			memcpy(data,olddata,_n_actual*_m*sizeof(T));
			if(!_isShared)
				delete[] olddata;
		}
		
		_n_actual=new_n_actual;
	}

	/// Determine a shared name based on the name stored in this matrix and the counter value, used to determine a system-wide unique name
	void chooseSharedName(int counter=0)
	{
		std::ostringstream out;
#ifdef WIN32
		out << "Local\\" ;

		if(counter>0)
			out << std::hex << counter << std::dec;

		out << GetCurrentProcessId() << _name;
		_sharedname=out.str();
#else

// OSX shm_open requires names to be shorter than normal
#ifdef __APPLE__
		if(counter>0)
			out << std::hex << counter << std::dec;

		out << getpid() << _name;
#else
		out << "__viz__" << getppid() << "_" << getpid();
		if(counter>0)
			out << "_" << std::hex << counter << std::dec;

		out << "_" << _name;
#endif // #ifdef __APPLE__

		_sharedname=out.str();
		
		for(sval i=0;i<_sharedname.size();i++)
			if(_sharedname[i]=='/')
				_sharedname[i]='_';

		if(_sharedname.size()>=MAXSHMNAMLEN)
			_sharedname[MAXSHMNAMLEN-1]='\0';
#endif // #ifdef WIN32
	}

	/// Create a shared segment and return a mapped pointer to it
	T* createShared() throw(MemException)
	{
		sval size=memSize();
		T* ptr;
		bool isCreator=_sharedname=="";

		if(isCreator)
			chooseSharedName(); // start with the default shared name

#ifdef WIN32
		std::ostringstream out;

		createFileMapping();
		
		// attempt to choose a unique shared name only when creating a segment
		for(int c=1;c<100000 && isCreator && mapFile && GetLastError()==ERROR_ALREADY_EXISTS;c++){
			CloseHandle(mapFile);
			chooseSharedName(c);
			createFileMapping();
		}

		if(!mapFile){
			out << "Unable to open shared memory handle to " << _sharedname << ": " << formatLastErrorMsg();
			throw MemException(out.str());
		}

		ptr=(T*)MapViewOfFile(mapFile,FILE_MAP_ALL_ACCESS,0,0,size);

		if(!ptr && isCreator && GetLastError()==ERROR_ACCESS_DENIED){
			for(int c=1;c<100000 && mapFile && !ptr && (GetLastError()==ERROR_ACCESS_DENIED || GetLastError()==ERROR_ALREADY_EXISTS);c++){
				CloseHandle(mapFile);
				chooseSharedName(c);
				createFileMapping();

				if(mapFile)
					ptr=(T*)MapViewOfFile(mapFile,FILE_MAP_ALL_ACCESS,0,0,size);
			}
		}

		if(!ptr){
			CloseHandle(mapFile);
			out << "Unable to map view of memory file " << _sharedname << ": " << formatLastErrorMsg();
			throw MemException(out.str());
		}

#else // Linux/OSX

		int shm_fd=shm_open(_sharedname.c_str(), O_CREAT | O_RDWR | (isCreator ? O_EXCL : 0), S_IRUSR | S_IWUSR);

		// attempt to choose a unique shared name only when creating a segment
		for(int c=1;c<100000 && isCreator && shm_fd==-1 && errno==EEXIST;c++){
			chooseSharedName(c);
			shm_fd=shm_open(_sharedname.c_str(), O_CREAT | O_RDWR | O_EXCL, S_IRUSR | S_IWUSR);
		}

		if(shm_fd==-1)
			throw MemException(std::string("Unable to open shared memory descriptor, filename:")+_sharedname,errno);

		if(isCreator && ftruncate(shm_fd, size) == -1)
			throw MemException(std::string("Unable to extend shared memory section, filename:")+_sharedname,errno);

		ptr = (T*)mmap(0, size, PROT_READ | PROT_WRITE, MAP_SHARED, shm_fd, 0);

		if(!ptr || ptr==MAP_FAILED){
			if(isCreator)
				shm_unlink(_sharedname.c_str());

			throw MemException("Unable to mmap shared memory",errno);
		}
		
		addShared(_sharedname); // store the name for later cleanup

		close(shm_fd);
#endif // Linux/OSX

		return ptr;
	}

	/// Unmap the given shared segment, and delete it if this object created it
	void closeShared(T* ptr) throw(MemException)
	{
		if(!ptr)
			return;

#ifdef WIN32
		if(!UnmapViewOfFile(ptr))
			throw MemException("Failed to unmap file view");

		if(!CloseHandle(mapFile))
			throw MemException("Failed to close handle");
#else
		int mures=munmap(ptr,memSize());    
		if(mures==-1)
			throw MemException("Failed to unmap memory section");
#endif // WIN32
		_sharedname="";
	}

#ifdef WIN32
	void createFileMapping()
	{
#ifdef UNICODE
		const char* name=_sharedname.c_str();
		wchar_t namebuff[1024];

		::MultiByteToWideChar(CP_ACP, NULL,name, -1, namebuff,int(_sharedname.size()+1));
#else
		const char* namebuff=_sharedname.c_str();
#endif

		mapFile = CreateFileMapping(INVALID_HANDLE_VALUE, NULL, PAGE_READWRITE, 0, DWORD(memSize()), namebuff);
	}
#endif // WIN32
};

typedef Matrix<real> RealMatrix;
typedef Matrix<vec3> Vec3Matrix;
typedef Matrix<indexval> IndexMatrix;
typedef Matrix<color> ColorMatrix;

/**
 * DataSet objects store a Vec3Matrix, IndexMatrix instances which represent node properties or topologies which
 * use the given nodes, and RealMatrix instances which represent field values for the nodes and/or for the topologies.
 * This is the main data structure passed around as the object encapsulating all the information about a model loaded
 * from external sources, or render data generated by algorithms. These must be implemented in Python so that the ownership
 * of the matrices remains in Python-space for garbage collection reasons. Matrices added to a PyDataSet object will be
 * associated with it for the lifetime of the of the data set, this ensures that they are only collected when needed and do
 * not leak if their ownership was transferred to C++.
 */
class DataSet : public MetaType
{
protected:
	std::string name;
	std::vector<std::string> indexnames;
	std::vector<std::string> fieldnames;

public:
	DataSet(const char* name): name(name) { }

	const char* getName() const { return name.c_str(); }
	
	virtual DataSet* clone(const char* name,bool cloneNodes=false){ return NULL;}

	virtual Vec3Matrix* getNodes() const { return NULL ;}
	virtual void setNodes(Vec3Matrix *nodes) { }
	
	/// Lists the names of index matrices stored
	virtual std::vector<std::string> getIndexNames() const { return indexnames; }
	
	/// Sets the internal list of index names, should be used to update name list whenever setIndexSet is called
	virtual void setIndexNames(std::vector<std::string> names) { indexnames=names; }

	/// Get the index matrix of the given name, or NULL if not found
	virtual IndexMatrix* getIndexSet(const char* name) const { return NULL; }

	/// Returns true if an index matrix of the given name is stored
	virtual bool hasIndexSet(const char* name) const { return getIndexSet(name)!=NULL; }
	
	/// Add a new index matrix to the data set using its internal name or the supplied name, replaces an existing stored matrix
	virtual void setIndexSet(IndexMatrix *indices,const char *alias=NULL) {}
	
	/// Lists the names of field matrices stored
	virtual std::vector<std::string> getFieldNames() const { return fieldnames; }
	
	/// Sets the internal list of field names, should be used to update name list whenever setDataField is called
	virtual void setFieldNames(std::vector<std::string> names) { fieldnames=names; }
	
	/// Get the field matrix of the given name, or NULL if not found
	virtual RealMatrix* getDataField(const char* name) const { return NULL; }
	
	/// Returns true if a field matrix of the given name is stored
	virtual bool hasDataField(const char* name) const { return getDataField(name)!=NULL; }
	
	/// Add a new field matrix to the data set using its internal name or the supplied name, replaces an existing stored matrix
	virtual void setDataField(RealMatrix *field,const char *alias=NULL) {}
};

/*****************************************************************************************************************************/
/* Scene Objects */
/*****************************************************************************************************************************/

class Material;

/// Represents a texture loaded into memory and available to the graphis hardware.
class Texture
{
public:
	Texture(){}
	virtual ~Texture() {}

	virtual const char* getName() const {return "";}
	virtual const char* getFilename() const {return "";}
	virtual sval getWidth() const { return 0;}
	virtual sval getHeight() const { return 0;}
	virtual sval getDepth() const { return 0; }
	virtual bool hasAlpha() const {return false;}
	virtual TextureFormat getFormat() const { return TF_UNKNOWN; }
	virtual void fillBlack() {}
	virtual void fillColor(color col) {}
	virtual void fillColor(const ColorMatrix *mat,indexval depth) {}
	virtual void fillColor(const RealMatrix *mat,indexval depth,real minval=0.0,real maxval=1.0, const Material* colormat=NULL,const RealMatrix *alphamat=NULL,bool mulAlpha=true) {}
};

/// Represents a GPU program (vertex/fragment/geometry shader)
class GPUProgram
{
public:
	virtual ~GPUProgram(){}

	virtual std::string getName() const {return "";}
	virtual void setType(ProgramType pt) {}
	virtual ProgramType getType() const { return PT_VERTEX; }
	virtual std::string getLanguage() const { return ""; }
	
	/// Set the language for the source of the program, eg. cg
	virtual void setLanguage(const std::string& lang) {}
	
	/// Set the source code for the program, this must be done in the main thread
	virtual void setSourceCode(const std::string& code){}
	
	/// Returns true if the source code given for the program has failed to parse
	virtual bool hasError() const { return false; }
	
	/// Return the text of the source for this program
	virtual std::string getSourceCode() const { return ""; }
	
	virtual bool setParameter(const std::string& param, const std::string& val) { return false; }
	virtual std::string getParameter(const std::string& param) const { return ""; }
	virtual std::string getEntryPoint() const { return getParameter("entry_point"); }
	virtual std::string getProfiles() const { return getParameter("profiles"); }
	virtual std::vector<std::string> getParameterNames() const { return std::vector<std::string>(); }
	virtual void setEntryPoint(const std::string main) { setParameter("entry_point",main); }
	virtual void setProfiles(const std::string profiles) { setParameter("profiles",profiles); }
};

template<typename T>
class PositionQueue
{
protected:
	typedef std::pair<real,T> ListValue;
	Matrix<ListValue> vals;

public:
	PositionQueue() : vals("vals",0) {}
	virtual ~PositionQueue() {}

	void copyFrom(const PositionQueue<T>* queue)
	{
		clear();
		vals.append(queue->vals);
	}

	void add(real pos,T val)
	{
		vals.append(ListValue(pos,val));
		sort();
	}

	void fill(const RealMatrix* pos, const Matrix<T>* ctrls)
	{
		vals.setN(pos->n());
		for(indexval i=0;i<pos->n();i++)
			vals[i]=ListValue(pos->at(i),ctrls->at(i));
	}

	sval size() const { return vals.n();}

	void clear() { vals.setN(0); }

	T get(indexval index) const throw(IndexException)
	{
		return vals.getAt(index).second;
	}

	void set(indexval index,real pos, T value) throw(IndexException)
	{
		vals.setAt(ListValue(pos,value),index);
		sort();
	}

	real pos(indexval index) const throw(IndexException)
	{
		return vals.getAt(index).first;
	}

	void remove(indexval index) throw(IndexException)
	{
		vals.removeRow(index);
		sort();
	}

	indexval find(real pos, const T& value) const
	{
		indexval i=0;
		sval numVals=vals.n();

		while(i<numVals && (!equalsEpsilon(vals[i].first,pos) || vals[i].second!=value))
			i++;

		return i;
	}

	void sort()
	{
		if(vals.n()>1)
			qsort(vals.dataPtr(),vals.n(),sizeof(ListValue),sortTupleFirstCB<ListValue>);
	}
};

/**
 * Defines a curve which passes through all of the control points given. This works by break the curve into piecewise 
 * cubic bezier splines and calculating derivatives that maintain a smooth slope between segments.
 * (http://www.codeproject.com/Articles/36375/Cubic-Bezier-Spline-Curves-and-Image-Curve-Adjustm)
 */
template<typename T>
class ControlCurve
{
protected:
	Matrix<T> ctrls;
	Matrix<T> derivs;

public:
	ControlCurve() : ctrls("ctrls","",0,1), derivs("derivs","",0,2) {}
	virtual ~ControlCurve() {} 

	void copyFrom(const ControlCurve<T> *con)
	{
		ctrls.setN(0);
		ctrls.append(con->ctrls);
		calculateDerivs();
	}

	void clear()
	{
		ctrls.setN(0);
		derivs.setN(0);
	}

	virtual void addCtrlPoint(const T& t) { ctrls.append(t); calculateDerivs(); }
	virtual void setCtrlPoint(const T& t,indexval index) throw(IndexException) { ctrls.setAt(t,index); calculateDerivs(); }
	virtual void removeCtrlPoint(indexval index) throw(IndexException) { ctrls.removeRow(index); calculateDerivs(); }
	virtual sval numPoints() const { return ctrls.n(); }
	virtual T getCtrlPoint(indexval index) const throw(IndexException) { return ctrls.getAt(index); }

	virtual void setCtrlPoints(const Matrix<T>* pts)
	{
		ctrls.setN(0);
		for(sval i=0;i<pts->n();i++)
			ctrls.append(pts->at(i));

		calculateDerivs();
	}

	virtual void calculateDerivs()
	{
		sval n=ctrls.n();
		derivs.setN(n);

		if(n==1){
			derivs(0,0)=ctrls[0];
			derivs(0,1)=ctrls[0];
		}
		else if(n==2){
			derivs(0,0)=ctrls[0];
			derivs(0,1)=ctrls[1];
			derivs(1,0)=ctrls[1];
			derivs(1,1)=ctrls[0];
		}
		else if(n>2){
			RealMatrix mat("",n,3);

			Matrix<T> localderivs("localderivs",n,1);

			localderivs[0]=ctrls[0];
			localderivs[n-1]=ctrls[n-1];

			if(n==3)
				localderivs[1]=ctrls[1]*6-ctrls[0]-ctrls[n-1];
			else{
				localderivs[1]=ctrls[1]*6-ctrls[0];
				localderivs[n-2]=ctrls[n-2]*6-ctrls[n-1];
			
				for(indexval i=2;i<n-2;i++)
					localderivs[i]=ctrls[i]*6;
			}

			for(indexval i=0;i<n;i++){
				mat(i,0)=4.0;
				mat(i,1)=1.0;
				mat(i,2)=1.0;
			}

			// Gaussian elimination
			for(indexval i=2;i<n-1;i++){
				mat(i,1)=mat(i,1)/mat(i-1,0);
				mat(i,0)=mat(i,0)-(mat(i,1)*mat(i-1,2));
				localderivs[i]=localderivs[i]-(localderivs[i-1]*mat(i,1));
			}

			localderivs[n-2]=localderivs[n-2]/mat(n-2,0);

			for(indexval i=n-3;i>0;i--)
				localderivs[i]=(localderivs[i]-(localderivs[i+1]*mat(i,2)))/mat(i,0);

			for(indexval s=0;s<n;s++){
				indexval e=clamp<indexval>(s+1,0,n-1);
				derivs(s,0)=(localderivs[s] * (2.0 / 3.0)) + (localderivs[e] / 3.0);
				derivs(s,1)=(localderivs[s] / 3.0) + (localderivs[e] * (2.0 / 3.0));
			}
		}
		// else n==0 do nothing
	}

	virtual T at(real tt) const
	{
		indexval n=ctrls.n();
		real tn=tt*(n-1);
		
		indexval s=clamp<indexval>(indexval(tn),0,n-1);
		indexval e=clamp<indexval>(indexval(tn)+1,0,n-1);
		
		real t=tn-s;
		real t1=1.0-t;
		
		T d1=derivs(s,0); 
		T d2=derivs(s,1); 

		return (ctrls[s]*(t1*t1*t1))+(ctrls[e]*(t*t*t))+(d1*(3*t1*t1*t))+(d2*(3*t1*t*t)); // cubic bezier spline
	}
};


/*template<typename T>
class ControlCurve
{
protected:
	Matrix<T> ctrls;

public:
	ControlCurve() : ctrls("ctrls","",0,1) {}
	virtual ~ControlCurve() {} 

	virtual void addCtrlPoint(const T& t) { ctrls.append(t); }
	virtual void setCtrlPoint(const T& t,indexval index) throw(IndexException) { ctrls.setAt(t,index); }
	virtual void removeCtrlPoint(indexval index) throw(IndexException) { ctrls.removeRow(index); }
	virtual sval numPoints() const { return ctrls.n(); }
	virtual T getCtrlPoint(indexval index) const throw(IndexException) { return ctrls.getAt(index); }

	virtual void setCtrlPoints(const Matrix<T>* pts)
	{
		ctrls.setN(0);
		for(sval i=0;i<pts->n();i++)
			ctrls.append(pts->at(i));
	}

	virtual void calculateDerivs(){}

	virtual T at(real tt) const
	{
		indexval n=ctrls.n();
		real tn=tt*(n-1);

		indexval s=clamp<indexval>(indexval(tn),0,n-1);
		indexval e=clamp<indexval>(indexval(tn)+1,0,n-1);
		indexval ds=clamp<indexval>(indexval(tn)-1,0,n-1);
		indexval de=clamp<indexval>(indexval(tn)+2,0,n-1);

		real t=tn-s;

		real t2=t*t;
		real t3=t2*t;
		real t3_05=t3*0.5;
		real t3_15=t3*1.5;
		real t_05=t*0.5;

		real cs=t3_15-2.5*t2+1;
		real ce=2*t2+t_05-t3_15;
		real dcs=t2-t_05-t3_05;
		real dce=t3_05-0.5*t2;

		T d1=ctrls[ds];
		T d2=ctrls[de];

		return ctrls[s]*cs+ctrls[e]*ce+d1*dcs+d2*dce;
	}
};*/

class Vec3Curve : public ControlCurve<vec3>
{
	bool isXFunc;
	bool isLinear;
public:
	Vec3Curve(bool isXFunc) : ControlCurve<vec3>(), isXFunc(isXFunc),isLinear(false) {}

	void setLinear(bool b) { isLinear=b; }
	bool isLinearFunc() const { return isLinear; }

	virtual void addCtrlPoint(const vec3& t)
	{
		vec3 tt=t;
		if(isXFunc){
			real minx=ctrls.n()==0 ? 0.0 : ctrls[ctrls.n()-1].x();
			tt=vec3(clamp<real>(t.x(),minx,1.0),clamp<real>(t.y(),0.0,1.0),0);
		}
		ControlCurve<vec3>::addCtrlPoint(tt);
	}

	virtual void setCtrlPoint(const vec3& t,indexval index) throw(IndexException)
	{
		vec3 tt=t;
		if(isXFunc){
			real minx=index==0 ? 0.0 : ctrls[index-1].x();
			tt=vec3(clamp<real>(t.x(),minx,1.0),clamp<real>(t.y(),0.0,1.0),0);
		}

		ctrls.setAt(tt,index); 

		if(isXFunc)
			for(sval i=index+1;i<ctrls.n();i++)
				ctrls[i].x(clamp<real>(ctrls[i].x(),ctrls[i-1].x(),1.0));

		calculateDerivs();
	}

	virtual void calculateDerivs()
	{
		if(isXFunc)
			qsort(ctrls.dataPtr(),ctrls.n(),sizeof(vec3),vec3::compX);
		
		ControlCurve<vec3>::calculateDerivs();
	}

	real atX(real x, real threshold=0.0001) const
	{
		if(x<=ctrls[0].x())
			return ctrls[0].y();

		if(x>=ctrls[ctrls.n()-1].x())
			return ctrls[ctrls.n()-1].y();

		if(isLinear){
			sval i=1;
			while(ctrls[i].x()<x)
				i++;

			real xi=lerpXi<real>(x,ctrls[i-1].x(),ctrls[i].x());
			return lerp<real>(xi,ctrls[i-1].y(),ctrls[i].y());
		}
		else{
			real start=0.0, end=1.0, mid=0.5;

			vec3 val=at(mid);
			real diff=val.x()-x;

			// bsearch for interpolated value whose X coord is close to `x'
			while(fabs(diff)>threshold && (end-start)>threshold){
				if(diff>0)
					end=mid;
				else
					start=mid;

				mid=start+(end-start)*0.5;
				val=at(mid);
				diff=val.x()-x;
			}

			return val.y();
		}
	}
};


class Spectrum
{
protected:
	PositionQueue<color> spec;

	Vec3Curve alphacurve;

	std::string name;

public:
	Spectrum(const std::string& name="") : alphacurve(true), name(name) {}

	virtual const char* getName() const { return name.c_str(); }

	virtual void clearSpectrum()
	{
		spec.clear();
		alphacurve.clear();
		updateSpectrum();
	}

	virtual void copySpectrumFrom(const Spectrum* s)
	{
		spec.copyFrom(&s->spec);
		alphacurve.copyFrom(&s->alphacurve);
		updateSpectrum();
	}
	
	virtual color getDefaultColor() const { return color(); }

	virtual real getAlpha() const { return 1.0; }

	virtual void updateSpectrum() {}

	/// Add a color value to the spectrum at the given position then resort the spectrum
	virtual void addSpectrumValue(real pos,color value)
	{
		spec.add(pos,value);
		updateSpectrum();
	}

	/// Get the position of the spectrum value at the given index in the list
	virtual real getSpectrumPos(indexval index) const throw(IndexException)
	{
		return spec.pos(index);
	}

	/// Get the color of the spectrum value at the given index in the list
	virtual color getSpectrumValue(indexval index) const throw(IndexException)
	{
		return spec.get(index);
	}

	/// Get the index of the spectrum value with the given position and color, returns numSpectrumValues() if not found
	virtual indexval getSpectrumIndex(real pos,color value) const
	{
		return spec.find(pos,value);
	}

	/// Set the spectrum value at the given list index
	virtual void setSpectrumValue(sval index, real pos,color value) throw(IndexException)
	{
		spec.set(index,pos,value);
		updateSpectrum();
	}

	/// Get the number of spectrum values
	virtual sval numSpectrumValues() const
	{
		return spec.size(); 
	}

	/// Remove the spectrum value at the given index
	virtual void removeSpectrumValue(indexval index) throw(IndexException)
	{
		spec.remove(index);
		updateSpectrum();
	}

	virtual sval numAlphaCtrls() const 
	{ 
		return alphacurve.numPoints(); 
	}

	virtual vec3 getAlphaCtrl(indexval index) const throw(IndexException) 
	{ 
		return alphacurve.getCtrlPoint(index); 
	}

	virtual void addAlphaCtrl(vec3 v) 
	{ 
		alphacurve.addCtrlPoint(v); 
		updateSpectrum();
	}

	virtual void removeAlphaCtrl(indexval index) throw(IndexException) 
	{
		alphacurve.removeCtrlPoint(index);
		updateSpectrum();
	}

	virtual void setAlphaCtrl(vec3 v, indexval index) throw(IndexException) 
	{
		alphacurve.setCtrlPoint(v,index);
		updateSpectrum();
	}

	virtual void setAlphaCurve(const Vec3Matrix* pts)
	{
		alphacurve.setCtrlPoints(pts);
		updateSpectrum();
	}

	virtual void setLinearAlpha(bool b)
	{
		alphacurve.setLinear(b);
		updateSpectrum();
	}

	virtual bool isLinearAlpha() const 
	{
		return alphacurve.isLinearFunc();
	}

	/**
	 * Interpolate a color with the spectrum at the given position. If `pos' is less than or equal to the
	 * position of the first spectrum value, that color is returned, if greater than or equal that of the 
	 * last spectrum value, that color is returned. If neither is true, there exists two values cmin and
	 * cmax such that the position of cmin is less than `pos' and that of cmax is greater. This method will
	 * then use the distance `pos' is from these other positions to interpolate between cmin and cmax.
	 */
	virtual color interpolateColor(real pos) const
	{
		color result;
		float alpha=getAlpha();
		indexval specsize=spec.size();

		if(specsize==0)
			result=getDefaultColor();
		else if(pos<=spec.pos(0))
			result= spec.get(0);
		else if(pos>=spec.pos(specsize-1))
			result=spec.get(specsize-1);
		else{
			sval index=0;
			while(index<specsize-1 && spec.pos(index+1)<pos)
				index++;

			color cmin=spec.get(index);
			color cmax=spec.get(index+1);

			real interp=lerpXi(pos,spec.pos(index),spec.pos(index+1));

			result= cmin.interpolate(interp,cmax);
		}

		if(alphacurve.numPoints()>1){
			real a=clamp<real>(alphacurve.atX(pos),0.0,1.0);
			if(alpha>=0.0 && specsize>0)
				a*=alpha;

			result.a(a);
		}
		else if(alpha>=0.0)
			result.a(alpha);

		return result;
	}
	
	/**
	 * Interpolate the colors from the material's spectrum into `col' using the unit values in the first column
	 * of `mat'. If `mat' has two columns, multiply the resulting color's alpha channel by the second column value.
	 */
	virtual void fillColorMatrix(ColorMatrix *col,const RealMatrix *mat,bool useValAsAlpha=false) throw(IndexException) 
	{
		bool hasMatAlpha=mat->m()>=col->m()*2;
		sval len=_min(col->n(),mat->n());
		sval width=_min(col->m(),mat->m());
		
		for(sval i=0;i<len;i++){
			for(sval j=0;j<width;j++){
				float val=mat->getAt(i,j);
				color c=interpolateColor(val);
				
				if(hasMatAlpha)
					c.a(mat->getAt(i,col->m()+j)*c.a());
				else if(useValAsAlpha)
					c.a(val*c.a());
				
				col->setAt(c,i,j);
			}
		}
	}
};


/** 
 * Materials encapsulate the lighting and color properties applied to renderable objects. This covers diffuse, specular, ambient,
 * and emissive light, point size for point objects, blending mode, and options on using vertex color, scene lighting, alpha
 * blending, and others. It also stores a spectrum of colors defined as color values positioned along the unit interval. Spectrums
 * are used to interpolate a color form a given unit value, this used for data coloration where field values are converted into
 * these unit values.
 */
class Material : public Spectrum
{
public:
	float alpha;
	bool useAlpha;

	Material() : alpha(1.0), useAlpha(true) {} 
	virtual ~Material(){}

	/// Make a copy of this material with the given name
	virtual Material* clone(const char* name) const { return NULL; }
	
	/// Copy this material's settings to `mat'
	virtual void copyTo(Material* mat,bool copyTex=false,bool copySpec=false,bool copyProgs=false) const {}
	
	/// Get the alpha (transparency) value, 1.0 is opaque and 0.0 is invisible, -1.0 if alpha shouldn't be used
	virtual real getAlpha() const { return useAlpha ? alpha : -1.0; }

	virtual color getDefaultColor() const { return getDiffuse(); }
	
	/// Set the internal alpha value, resetting the diffuse and specular values expected a subtype to set the alpha components for these
	virtual void setAlpha(real alpha)
	{
		this->alpha=(float)alpha;
		setDiffuse(getDiffuse());
		setSpecular(getSpecular());
	}

	/// Returns true if the internal alpha value is to be applied to colors, otherwise the alpha components of colors are used as inputed
	virtual bool usesInternalAlpha() const { return useAlpha; }
	
	/// Set whether to use the internal alpha value or use those specified in the diffuse and specular color values
	virtual void useInternalAlpha(bool val)
	{
		useAlpha=val;
		setDiffuse(getDiffuse());
		setSpecular(getSpecular());
	}

	virtual color getAmbient() const { return color(); }
	virtual color getDiffuse() const { return color(); }
	virtual color getSpecular() const { return color(); }
	virtual color getEmissive() const { return color(); }

	virtual real getShininess() const { return 0.0f; }
	virtual real getPointSizeMin() const { return 0.0f; }
	virtual real getPointSizeMax() const { return 0.0f; }
	virtual real getPointSizeAbs() const { return 0.0f; }
	virtual bool usesPointAttenuation() const { return false; }
	virtual BlendMode getBlendMode() const { return BM_ALPHA; }

	virtual bool usesVertexColor() const { return false; }
	virtual bool usesLighting() const { return false; }
	virtual bool usesFlatShading() const { return false; }
	virtual bool usesDepthCheck() const { return false; }
	virtual bool usesDepthWrite() const { return false; }
	virtual bool usesTexFiltering() const { return false; }
	virtual bool isClampTexAddress() const { return false;}
	virtual bool isCullBackfaces() const { return false; }
	virtual bool usesPointSprites() const { return false; }
	virtual const char* getTexture() const { return ""; }
	virtual const char* getGPUProgram(ProgramType pt) const {  return ""; }

	virtual int getGPUParamInt(ProgramType pt, const std::string& name) { return 0; }
	virtual real getGPUParamReal(ProgramType pt, const std::string& name) { return 0; }
	virtual vec3 getGPUParamVec3(ProgramType pt, const std::string& name) { return vec3(); }
	virtual color getGPUParamColor(ProgramType pt, const std::string& name) { return color(); }

	/// Returns true if the intenal alpha value is used, if it's <1.0, if vertex colors are not used, and if no textur is assigned
	virtual bool isTransparentColor() const { return useAlpha && alpha<1.0 && !usesVertexColor() && !strcmp(getTexture(),""); }

	virtual void setAmbient(const color & c) {}
	/// Sets the diffuse color, if usesInternalAlpha() returns true the alpha value will be set the internal value
	virtual void setDiffuse(const color & c){}
	/// Sets the specular color, if usesInternalAlpha() returns true the alpha value will be set the internal value
	virtual void setSpecular(const color & c){}
	virtual void setEmissive(const color & c) {}
	/// Set the amount of specular hightlighting to apply
	virtual void setShininess(real c){}
	
	/// Set the minimum and maximum point size for attenuated points
	virtual void setPointSize(real min,real max) {}
	/// Set the absolute point size
	virtual void setPointSizeAbs(real size) {}
	/// Sets point attenuation, the given real values are constants the attenuation equation
	virtual void setPointAttenuation(bool enabled,real constant=0.0f,real linear=1.0f, real quad=0.0f) {}
	
	virtual void setBlendMode(BlendMode bm) {}
	virtual void useVertexColor(bool use) {}
	virtual void useLighting(bool use) {}
	virtual void useFlatShading(bool use) {}
	virtual void useDepthCheck(bool use) {}
	virtual void useDepthWrite(bool use) {}
	virtual void useTexFiltering(bool use) {}
	virtual void clampTexAddress(bool use) {}
	virtual void cullBackfaces(bool cull) {}
	virtual void usePointSprites(bool useSprites){}
	virtual void setTexture(const char* name){}
	virtual void setTexture(const Texture* tex) { setTexture(tex->getName()); }

	virtual void useSpectrumTexture(bool use) {}
	
	virtual void setGPUProgram(const std::string& name, ProgramType pt) {}
	virtual void setGPUProgram(const GPUProgram *prog) { setGPUProgram(prog->getName(),prog->getType()); }

	virtual bool setGPUParamInt(ProgramType pt,const std::string& name, int val) { return false; }
	virtual bool setGPUParamReal(ProgramType pt,const std::string& name, real val) { return false; }
	virtual bool setGPUParamVec3(ProgramType pt,const std::string& name, vec3 val) { return false; }
	virtual bool setGPUParamColor(ProgramType pt,const std::string& name, color val) { return false; }

	virtual void updateSpectrum() {}
};

/**
 * A light represents a point in space which emits light either in all directions or as a spotlight, or a directed
 * light source which illuminates all objects in the scene from one direction. 
 */
class Light
{
public:
	Light(){}
	virtual ~Light() {}

	/// Set the position for this light, only meaningful for point and spot lights
	virtual void setPosition(vec3 &v){}
	
	/// Set the direction to emit light at, only meaningful for directional and spot lights
	virtual void setDirection(vec3 &v){}
	
	/// Set the diffuse color to emit
	virtual void setDiffuse(const color & c){}
	
	/// Set the specular color to reflect
	virtual void setSpecular(const color & c){}

	/// Make this a directional light, illuminating all scene objects in the set direction 
	virtual void setDirectional() {}
	
	/// Make this a point light, illuminating all objects within range as defined by the attenuation settings
	virtual void setPoint() {}
	
	/// Make this a spot light with the given beam angles and falloff values
	virtual void setSpotlight(real radsInner, real radsOuter, real falloff=1.0f) {}
	
	/// Set the attenuation values for spot and point lights
	virtual void setAttenuation(real range, real constant=0.0f,real linear=1.0f, real quad=0.0f) {}

	/// Set whether this light is currently illuminating or not
	virtual void setVisible(bool isVisible){}
	
	/// Returns true if this light is actively illuminating the scene
	virtual bool isVisible() const { return false; }
};

/** 
 * A VertexBuffer is used by Figure objects to fill their internal representations with vertex, normal, color, and texture 
 * UV coords. This can be subtyped in Python to adapt Python data structures to C++ for small figures.
 */
class VertexBuffer
{
public:
	virtual ~VertexBuffer() {}

	/// Returns the i'th vertex, i<numVertices()
	virtual vec3 getVertex(int i) const { return vec3(0,0,0); }
	/// Returns the i'th normal, i<numVertices()
	virtual vec3 getNormal(int i) const { return vec3(0,0,0); }
	/// Returns the i'th color, i<numVertices()
	virtual color getColor(int i) const { return color(0,0,0,0); }
	/// Returns the i'th UVW texture coord, i<numVertices()
	virtual vec3 getUVWCoord(int i) const { return vec3(0,0,0); }

	/// Returns number of total vertices
	virtual sval numVertices() const { return 0; }
	/// Returns true if the buffer contains normal data
	virtual bool hasNormal() const { return false; }
	/// Returns true if the buffer contains color data
	virtual bool hasColor() const { return false; }
	/// Returns true if the buffer contains texture coord data
	virtual bool hasUVWCoord() const { return false; }
};

/// An IndexBuffer is used by Figure objects to read in the topologies for the figures to render, and can also be subtyped in Python.
class IndexBuffer
{
public:
	virtual ~IndexBuffer() {}
	
	///Returns the number of index sets
	virtual sval numIndices() const { return 0; }
	/// Returns the width of index set i, i<numIndices(). All index sets for now are assumed to be the same width 
	virtual sval indexWidth(int i) const { return 0; }
	/// Returns the w'th value of index set i
	virtual sval getIndex(int i,int w) const { return 0; }
};

/**
 * This buffer uses callback functions passed to its constructor as the sources of data rather than storing matrices. The
 * purpose is to allow the callback functions to be defined in Cython to adapt Python code/objects to C++. This allows a 
 * VertexBuffer subtype to be defined with Python code but callable in C++. The Ctx value is the context the callback 
 * functions are given when called which is typically going to be `this' cast to a different type in Cython such as void*.
 */
template<typename Ctx>
class CallbackVertexBuffer : public VertexBuffer
{
public:
	typedef vec3 (*vecfunc)(Ctx,int);
	typedef color (*colfunc)(Ctx,int);

	vecfunc vertfunc;
	vecfunc normalfunc;
	colfunc colorfunc;
	vecfunc uvwfunc;
	sval numvertices;
	Ctx context;

	CallbackVertexBuffer(Ctx context, sval numvertices, vecfunc vertfunc, vecfunc normalfunc=NULL, colfunc colorfunc=NULL, vecfunc uvwfunc=NULL):
		vertfunc(vertfunc),normalfunc(normalfunc),colorfunc(colorfunc),uvwfunc(uvwfunc),numvertices(numvertices),context(context)
	{ }

	virtual vec3 getVertex(int i) const { return vertfunc(context,i); }	
	virtual vec3 getNormal(int i) const { return normalfunc(context,i); }	
	virtual color getColor(int i) const { return colorfunc(context,i); }	
	virtual vec3 getUVWCoord(int i) const { return uvwfunc(context,i); }

	virtual sval numVertices() const { return numvertices; }
	virtual bool hasNormal() const { return normalfunc!=NULL; }
	virtual bool hasColor() const { return colorfunc!=NULL; }
	virtual bool hasUVWCoord() const { return uvwfunc!=NULL; }
};

/// See CallbackVertexBuffer, the same concept applies here with a buffer accepting functions defined in Cython to adapt Python code.
template<typename Ctx>
class CallbackIndexBuffer : public IndexBuffer
{
public:
	typedef sval (*wfunc)(Ctx,int);
	typedef sval (*ifunc)(Ctx,int,int);

	wfunc widthfunc;
	ifunc indexfunc;

	sval numindices;
	Ctx context;

	CallbackIndexBuffer(Ctx context, sval numindices, wfunc widthfunc,ifunc indexfunc):
		widthfunc(widthfunc), indexfunc(indexfunc), numindices(numindices), context(context)
	{}

	virtual sval numIndices() const { return numindices; }
	virtual sval indexWidth(int i) const { return widthfunc(context,i); }
	virtual sval getIndex(int i,int w) const { return indexfunc(context,i,w); }
};

/**
 * Implementation of a VertexBuffer which uses matrices for storage. This assumes the input Vec3Matrix has 1, 2, or 4
 * columns, which are the position, normal, xi coordinate, and UVW coordinate components per node. The method hasNormal()
 * returns true if there's more than one column, and hasUVWCoord() is true if there's more than 3, therefore the xi column
 * must be present but is ignored. A copy constructor allows the copying of buffer data into a MatrixVertexBuffer object
 * which retains ownership of the internal matrices and delete them when cleaned up. Matrices passed in through the normal
 * constructor remain the responsibility of the caller.
 */
class MatrixVertexBuffer : public VertexBuffer
{
	Vec3Matrix* vecs;
	ColorMatrix* cols;
	IndexMatrix* extinds;
	sval numverts;
	bool deleteMatrices;

public:
	/// Create the buffer from these matrices, vecs.m() in (1,2,4). The caller is responsible for deleting these when appropriate
	MatrixVertexBuffer(Vec3Matrix* vecs,ColorMatrix* cols=NULL,IndexMatrix* extinds=NULL) throw(RenderException) 
		: vecs(vecs), cols(cols),extinds(extinds), deleteMatrices(false)
	{
		if(vecs==NULL)
			throw RenderException("Matrix 'vecs' must be provided");

		numverts=sval(extinds!=NULL ? extinds->n() : vecs->n());
	}
	
	/// Copy the data from `buf' into internal matrices which this object is responsible for and will delete in its destructor
	MatrixVertexBuffer(const VertexBuffer* buf) throw(RenderException) : numverts(buf ? buf->numVertices() : 0), cols(NULL), extinds(NULL), deleteMatrices(true)
	{
		if(!numverts)
			throw RenderException("VertexBuffer 'buf' must be provided");
		
		int columns=1;
		if(buf->hasUVWCoord())
			columns=4;
		else if(buf->hasNormal())
			columns=2;
		
		vecs=new Vec3Matrix("copyvecs",buf->numVertices(),columns);
		
		if(buf->hasColor())
			cols=new ColorMatrix("copycols",buf->numVertices());
		
		for(sval i=0;i<numverts;i++){
			vecs->at(i,0)=buf->getVertex(i);
			if(buf->hasNormal())
				vecs->at(i,1)=buf->getNormal(i);
			if(buf->hasUVWCoord())
				vecs->at(i,3)=buf->getUVWCoord(i);
			
			if(buf->hasColor())
				cols->at(i)=buf->getColor(i);
		}
	}
	
	virtual ~MatrixVertexBuffer()
	{
		if(deleteMatrices){
			SAFE_DELETE(vecs);
			SAFE_DELETE(cols);
			SAFE_DELETE(extinds);
		}
	}

	sval getIndex(sval i) const { return extinds!=NULL ? extinds->at(i) : i; }

	virtual vec3 getVertex(int i) const { return vecs->at(getIndex(i)); }
	virtual vec3 getNormal(int i) const { return vecs->at(getIndex(i),1); }
	virtual color getColor(int i) const { return cols->at(getIndex(i)); }
	virtual vec3 getUVWCoord(int i) const { return vecs->at(getIndex(i),3); }

	virtual sval numVertices() const { return numverts; }
	virtual bool hasNormal() const { return vecs->m()>1; }
	virtual bool hasColor() const { return cols!=NULL; }
	virtual bool hasUVWCoord() const { return vecs->m()>3; }
};

/// Implementation of a IndexBuffer which uses matrices for storage, like MatrixVertexBuffer.
class MatrixIndexBuffer : public IndexBuffer
{
	IndexMatrix* indices;
	IndexMatrix* extinds;
	bool deleteMatrices;
	
public:
	/// Create the buffer from these matrices. The caller is responsible for deleting these when appropriate
	MatrixIndexBuffer(IndexMatrix* indices,IndexMatrix* extinds=NULL) : indices(indices), extinds(extinds), deleteMatrices(false)
	{}
	
	/// Copy the data from `buf' into internal matrices which this object is responsible for and will delete in its destructor
	MatrixIndexBuffer(const IndexBuffer* buf) throw(RenderException) : extinds(NULL), deleteMatrices(true)
	{
		if(!buf)
			throw RenderException("IndexBuffer 'buf' must be provided");
		
		indices=new IndexMatrix("copyinds",buf->numIndices(),buf->indexWidth(0));
		
		for(sval i=0;i<buf->numIndices();i++)
			for(sval j=0;j<_min(indices->m(),buf->indexWidth(i));j++)
				indices->at(i,j)=buf->getIndex(i,j);
	}
	
	virtual ~MatrixIndexBuffer()
	{
		if(deleteMatrices){
			SAFE_DELETE(indices);
			SAFE_DELETE(extinds);
		}
	}

	virtual sval numIndices() const
	{
		if(indices==NULL)
			return 0;
		else if(extinds!=NULL)
			return sval(extinds->n());
		else
			return sval(indices->n());
	}
	virtual sval indexWidth(int i) const { return sval(indices!=NULL ? indices->m() : 0); }
	virtual sval getIndex(int i,int j) const { return sval(indices->getAt(extinds!=NULL ? extinds->getAt(i) : i,j)); }
};

/// Represents a ray emanating from a point and moving in a direction. It provides methods for doing intersection tests.
class Ray
{
	vec3 pos,dir,invdir;
	bool signx,signy,signz;
public:

	Ray()
	{}

	Ray(const vec3 &pos, const vec3 &dir): pos(pos)
	{
		setDirection(dir);
	}

	Ray(const Ray& r) : pos(r.pos)
	{
		setDirection(r.dir);
	}
	
	/// Get a position on the line at distance t, ie. t=0 is the origin
	vec3 getPosition(real t=0) const { return pos+(dir*t); }

	/// Get the direction the ray is pointing
	vec3 getDirection() const { return dir; }

	/// Set the origin of the ray, this is what getPosition(0) shall return
	void setPosition(const vec3 &v) { pos=v; }

	/// Set the direction the ray is pointing
	void setDirection(const vec3 &v)
	{
		if(v.isZero())
			throw std::invalid_argument("Direction vector is zero length.");
		
		dir=v.norm();
		
		// store the direction inverse for bound box check efficiency
		invdir=dir.inv();
		
		// store component signs for bound box check efficiency
		signx=invdir.x()<0;
		signy=invdir.y()<0;
		signz=invdir.z()<0;
	}

	/// Returns the distance to the projection of `v' on the ray, which is at getPosition(distTo(v)).
	real distTo(const vec3 v) const { return dir.dot(v-pos); }
	
	/**
	 * Returns the `t' value where the ray intersects the plane defined by the given position and normal. If the
	 * ray points away from the plane, the result is negative. If the ray is parallel with the plane and above it
	 * (ie. plane normal points towards ray origin), the result is negative infinity, if below positive infinity.
	 */
	real intersectsPlane(const vec3 & planepos, const vec3 & planenorm) const
	{
		return planenorm.dot(planepos-pos)/planenorm.dot(dir);
	}
	
	/** 
	 * Returns a pair (n,m) indicating that the ray passes through the AABB at t=n and t=m.
	 * Otherwise resturns (-1,-1) indicating that it does not pass through at all, or that the
	 * ray origin was in the bound box.
	 */
	realpair intersectsAABB(const vec3& minv, const vec3& maxv) const
	{
		real tmin, tmax, tymin, tymax, tzmin, tzmax;

		tmin  = ((signx ? maxv : minv).x() - pos.x()) * invdir.x();
		tmax  = ((signx ? minv : maxv).x() - pos.x()) * invdir.x();
		tymin = ((signy ? maxv : minv).y() - pos.y()) * invdir.y();
		tymax = ((signy ? minv : maxv).y() - pos.y()) * invdir.y();

		if ( (tmin > tymax) || (tymin > tmax) ) 
			return realpair(-1,-1);

		if (tymin > tmin)
			tmin = tymin;
		if (tymax < tmax)
			tmax = tymax;

		tzmin = ((signz ? maxv : minv).z() - pos.z()) * invdir.z();
		tzmax = ((signz ? minv : maxv).z() - pos.z()) * invdir.z();

		if ( (tmin > tzmax) || (tzmin > tmax) ) 
			return realpair(-1,-1);

		if (tzmin > tmin)
			tmin = tzmin;
		if (tzmax < tmax)
			tmax = tzmax;

		return realpair(tmin,tmax);//tmin < to && tmax > from;
	}
	
	/** 
	 * Returns a pair (n,m) indicating that the ray passes through the sphere at t=n and t=m.
	 * If n==m==0 then ray touches sphere at a single point. If n==m and n>0 then ray does not
	 * pass through the sphere but the projection of the sphere's center on the ray is at t=n.
	 * If n==m and n<0 then sphere is behind the ray and the projection is also at t=n. 
	 */
	realpair intersectsSphere(const vec3& center, real rad) const
	{
		real tca = distTo(center); // distance from `pos' to projection of `center' on the ray
		real thc=0; // offset from project of `center' on the ray where the sphere is intersected
	
		if(tca>0){ // if tca is positive, the sphere is in front of the ray, otherwise the result is where the sphere center projects on the ray
			real r2=rad*rad;
			vec3 L = center - pos;
			real d2 = L.dot(L) - tca * tca;
		
			if (d2 < r2) // ray intersects sphere at 2 points offset by thc, otherwise ray passes outside of sphere
				thc = sqrt(r2 - d2);
		}		

		return realpair(tca - thc, tca + thc); // thc==0 if ray does not pass through sphere, so tca is projection distance either in front or behind
	}

	/**
	 * Returns a pair (n,m) indicating that `this' intersects `ray' at t=n and `ray' intersects `this' at t=m. If both values are 0 then the rays do 
	 * not intersect, except for the special case where the origins of both are the same thus t is actually 0 for both.
	 */
	realpair intersectsRay(const Ray& ray) const
	{
		real t=0,s=0;
		vec3 p1=pos;
		vec3 p2=ray.getPosition();
		real t1=distTo(p2);
		real t2=ray.distTo(p1);
		vec3 pt1=getPosition(t1);
		vec3 pt2=ray.getPosition(t2);

		if(p2==pt1 || p1==pt2){ // check if either ray is pointing at the other
			if(p2==pt1) // this was pointing at `ray'
				t=t1;
			if(p1==pt2) // `ray' was pointing at this
				s=t2;
		}
		else{ 
			vec3 norm=p1.planeNorm(p2,getPosition(1.0)); // calculate a normal based on the two origins at the point at t=1.0
			if(ray.getPosition(1.0).onPlane(p1,norm)){ // if the point for `ray' at t=1.0 is on the plane then the rays intersect if they aren't parallel
				vec3 rd=ray.getDirection();
				real angle=dir.angleTo(rd);

				if(angle>dEPSILON && angle<(dPI-dEPSILON)){ // rays are not parallel
					t=intersectsPlane(p2,rd.cross(norm)); // find where this intersects the plane defined by `ray' at right angle to the plane this and `ray' lie on
					s=ray.distTo(getPosition(t)); // find the intersect distance for `ray' by seeing how far away the interect point for this is
				}
			}
		}

		return realpair(t,s);
	}
	
	/// Returns 0 if `v1' or `v2' are the origin of this ray, a value t >= 0 if the ray intersects the line at position t, -1 if the line is not intersected. 
	real intersectsLineSeg(const vec3& v1, const vec3& v2) const
	{
		real dist=intersectsPlane(v1,pos.planeNorm(v1,v2).cross(v2-v1));
		if(dist>=0 && dist<realInf && equalsEpsilon(getPosition(dist).lineDist(v1,v2),0))
				return dist;
		
		return -1;
	}

	/**
	 * Returns a triple (t,u,v) where t>=0 indicating that the ray passes through the triangle at 
	 * distance t. If t<0 then the ray does not pass through the triangle. The coord (u,v) is the 
	 * relative xi coord such that a point p on the triangle is p=(1-u-v)*v0+u*v1+v*v2, u+v<=1.
	 */
	realtriple intersectsTri(const vec3& v0, const vec3& v1, const vec3& v2) const 
	{
		vec3 e1=v1-v0; // triangle edge 1
		vec3 e2=v2-v0; // triangle edge 2
		vec3 p=dir.cross(e2); // direction perpendicular to ray line and edge 2
		real det=e1.dot(p); // determinant, will be 0 if edge 1 and p are perpendicular

		if(equalsEpsilon(det,0.0)) // ray is parallel with triangle's plane
			return realtriple(-1,-1,-1);

		real invdet=1.0/det;

		vec3 t=pos-v0;
		real u=p.dot(t)*invdet;

		if(u < 0 || u > 1) // ray intersects triangle's plane outside the band parallel with e1
			return realtriple(-1,-1,-1);

		vec3 q=t.cross(e1);
		real v=dir.dot(q)*invdet;

		if(v < 0 || u + v  > 1) // ray intersects triangle's plane outside the band parallel with e2 or outside the triangle area
			return realtriple(-1,-1,-1);
 
		real len=e2.dot(q)*invdet;

		if(len>dEPSILON) // ray points away from triangle
			return realtriple(len,u,v);
	
		return realtriple(-1,-1,-1);
	}
	
	/** 
	 * For each triangle the ray passes through, the result will contain an indexed triple whose first value is the index 
	 * in `inds' of the intersected triangle and the second is the result from intersectsTri() for that triangle. The
	 * intersected mesh is defined by the points `nodes' and triangle topology `inds'. The `centers' matrix is the center
	 * of the bounding spehere of each triangle in `inds', and `radii2' is the squared radius of each triangle's bounding 
	 * sphere. If `numResults' is greater than 0 only that many results will be returned. if `excludeInd' is greater than
	 * -1 the triangle at that index is skipped, this is useful for rays which begin at a triangle and are used to check
	 * for intersection with other parts of the same mesh.
	 */
	std::vector<indextriple> intersectsTriMesh(const Vec3Matrix* const nodes, const IndexMatrix* const inds,
		const Vec3Matrix* const centers, const RealMatrix* const radii2, sval numResults=0,sval excludeInd=-1) const  throw(IndexException)
	{
		std::vector<indextriple> results;
		sval len=inds->n();
		
		if(centers && radii2)
			len=_min(len,_min(centers->n(),radii2->n()));

		for(sval n=0;n<len && (numResults==0 || results.size()<numResults);n++){
			if(n==excludeInd)
				continue;

			vec3 ncenter,npos,v0,v1,v2;
			real nrad=0;
			
			if(centers && radii2){
				ncenter=centers->at(n);
				nrad=radii2->at(n);
				npos=getPosition(ncenter.distTo(pos));
	
				if(npos.distToSq(ncenter)>nrad)
					continue;
				
				v0=nodes->getAt(inds->at(n,0));
				v1=nodes->getAt(inds->at(n,1));
				v2=nodes->getAt(inds->at(n,2));
			}
			else{
				v0=nodes->getAt(inds->at(n,0));
				v1=nodes->getAt(inds->at(n,1));
				v2=nodes->getAt(inds->at(n,2));
				
				ncenter=(v0+v1+v2)/3.0;
				nrad=_max(ncenter.distToSq(v0),_max(ncenter.distToSq(v1),ncenter.distToSq(v2)));
				npos=getPosition(ncenter.distTo(pos));
	
				if(npos.distToSq(ncenter)>nrad)
					continue;
			}
			
			realtriple inter=intersectsTri(v0,v1,v2);
			
			if(inter.first>=0)
				results.push_back(indextriple(indexval(n),inter));
		}
		
		return results;
	}
};

/** 
 * Represents the combination of translation, scale, and rotation operations. When multiplying a vector v
 * by a transform t, the order of operations is to scale, rotate, then translate. If isInverse() is true
 * then the order is reversed. This type doesn't allow arbitrary operation orders or other transforms like
 * shear thus isn't as general as a 4x4 matrix. The advantage is that the translation, scale, and rotation 
 * components are defined separately and can be accessed or modified independently. A transform has an 
 * matrix equivalent, transforms can thus be compounded through matrix multiplication.
 */
class transform
{
public:
	vec3 trans;
	vec3 scale;
	rotator rot;
	bool _isInverse;

	/// Define a transform with translation and scale vectors and a rotator, default values define the identity transform.
	transform(const vec3& trans=vec3(),const vec3& scale=vec3(1.0),const rotator& rot=rotator(),bool isInv=false) : 
			trans(trans),scale(scale),rot(rot),_isInverse(isInv)
	{}

	transform(const transform & t) : trans(t.trans),scale(t.scale),rot(t.rot),_isInverse(t.isInverse())
	{}

	/// Define a transform with translation, scale, and Euler angle values.
	transform(real x, real y, real z, real sx, real sy, real sz, real yaw, real pitch, real roll, bool isInv=false) :
		trans(x,y,z), scale(sx,sy,sz),rot(yaw,pitch,roll), _isInverse(isInv)
	{}

	vec3 getTranslation() const { return trans; }
	vec3 getScale() const { return scale; }
	rotator getRotation() const { return rot; }

	bool isInverse() const { return _isInverse; }

	void setTranslation(const vec3 &v){ trans=v; }
	void setScale(const vec3 &v) { scale=v; }
	void setRotation(const rotator &r) { rot=r; }

	/// Transforms `v' by scaling->rotating->translating if not an inverse transform, otherwise by translating->rotating->scaling
	vec3 operator * (const vec3 &v) const
	{
		if(_isInverse)
			return scale*(rot*(v+trans));
		else
			return trans+(rot*(v*scale));
	}

	/// Commutative version of the above
	friend vec3 operator * (const vec3 &v, const transform &t)
	{
		return t*v;
	}

	/// Transform `v' by the inverse of `this'.
	vec3 operator / (const vec3 &v) const
	{
		return inverse()*v;
	}

	/// Commutative version of the above
	friend vec3 operator / (const vec3 &v, const transform &t)
	{
		return t/v;
	}

	friend vec3& operator *= (vec3 &v, const transform &t)
	{
		vec3 vv=t*v;
		v.x(vv.x());
		v.y(vv.y());
		v.z(vv.z());
		return v;
	}
	
	/// Transforms `r' by transforming its position by `this' but it direction by the directional components only of `this'.
	Ray operator * (const Ray &r) const
	{
		transform t=*this;
		return Ray(t*r.getPosition(),t.directional()*r.getDirection());
	}
	
	/// Commutative version of the above
	friend Ray operator * (const Ray &r, const transform &t)
	{
		return t*r;
	}

	/** 
	 * Calculate the transform representing the application of `t' followed by `this'. This transform isn't always equivalent
	 * to applying `t' to an object followed by `this'. If a combination of rotation and scaling values in `t' or `this' results
	 * skew then the transform produced by this operator will scale and rotate in unexpected ways. Skew is the result of applying
	 * affine operations in an order which produces a non-affine total result. 
	 *
	 * This method operates by producing a transform whose position that of `t' plus that of `this' transformed by the directional 
	 * components of `t', with a scale and rotation values which are the products of those from `t' and `this'. 
	 */
	transform operator * (const transform& t) const
	{
		/*vec3 nscale=t.getScale()*scale;
		rotator nrot=rot*t.getRotation();
		vec3 ntrans=t.getTranslation()+(trans*t.directional());
		return transform(ntrans,nscale,nrot);*/
		transform _t=*this; 
		vec3 mincorner=_t*(t*vec3(0)); 
		vec3 maxcorner=_t*(t*vec3(1)); 
		vec3 xcorner=_t*(t*vec3(1,0,0)); 
		vec3 ycorner=_t*(t*vec3(0,1,0)); 
		rotator rot((xcorner-mincorner).norm(),(ycorner-mincorner).norm(),vec3(1,0,0),vec3(0,1,0));
		vec3 scale=rot/(maxcorner-mincorner);
		return transform(mincorner,scale,rot); 
	}

	bool operator == (const transform & t) const
	{
		return trans==t.trans && scale==t.scale && rot==t.rot && _isInverse==t._isInverse;
	}

	/// Get the inverse transform of `this', ie. for any transform t and vec3 v (t.inverse()*(t*v)) is a no-op.
	transform inverse() const
	{
		return transform(trans*-1,scale.inv(),rot.inverse(),!_isInverse);
	}

	/// Get the directional version of this transform which is suitable for transforming directional vectors correctly, ie. no translation component.
	transform directional() const
	{
		return transform(vec3(),scale,rot,_isInverse);
	}

	/// Fill in the 4x4 matrix representing this transform. This assumes `mat' has length 16.
	void toMatrix(real* mat) const
	{
		rot.toMatrix(mat);
		if(_isInverse){
			mat[ 0]*=scale.x();
			mat[ 1]*=scale.x();
			mat[ 2]*=scale.x();
			mat[ 4]*=scale.y();
			mat[ 5]*=scale.y();
			mat[ 6]*=scale.y();
			mat[ 8]*=scale.z();
			mat[ 9]*=scale.z();
			mat[10]*=scale.z();
			mat[ 3]=trans.dot(vec3(mat[0],mat[1],mat[2]));
			mat[ 7]=trans.dot(vec3(mat[4],mat[5],mat[6]));
			mat[11]=trans.dot(vec3(mat[8],mat[9],mat[10]));
		}
		else{
			mat[ 0]*=scale.x();
			mat[ 1]*=scale.y();
			mat[ 2]*=scale.z();
			mat[ 4]*=scale.x();
			mat[ 5]*=scale.y();
			mat[ 6]*=scale.z();
			mat[ 8]*=scale.x();
			mat[ 9]*=scale.y();
			mat[10]*=scale.z();
			mat[ 3]=trans.x();
			mat[ 7]=trans.y();
			mat[11]=trans.z();
		}
	}

	mat4 toMatrix() const
	{
		mat4 m;
		toMatrix((real*)m.m);
		return m;
	}

	friend std::ostream& operator << (std::ostream &out, const transform &t)
	{
		return out << "transform(" << t.getTranslation() << ", " << t.getScale() << ", " << t.getRotation() << ", " << (t.isInverse() ? "true" : "false") << ")";
	}
};

/// Image objects represented loaded image files. These are used to access image data in code rather than load it into the renderer.
class Image
{
public:
	virtual ~Image() {} 

	/// Get the loaded data's format
	virtual TextureFormat getFormat() const { return TF_UNKNOWN; }
	/// Get the image width
	virtual sval getWidth() const { return 0; }
	/// Get the image height
	virtual sval getHeight() const { return 0; }
	/// Get the image depth
	virtual sval getDepth() const { return 0; }
	/// Get the image data size in bytes
	virtual size_t getDataSize() const { return 0; }
	/// Get a pointer to the internal data buffer
	virtual u8* getData() { return 0; }
	/// Encode the image data as the byte stream for a file, the format of which is given by `format' (eg. png, jpg)
	virtual std::string encode(const std::string& format) { return ""; }
	/// Transfer the image data into the given matrix
	virtual void fillRealMatrix(RealMatrix* mat) throw(IndexException) {}
	/// Transfer the image data into the given matrix
	virtual void fillColorMatrix(ColorMatrix* mat) throw(IndexException) {} 
};

/**
 * A notional camera in a scene defined by a point in space and the directional vectors describing its orientation. A viewport
 * relates a camera to a render target, in this case a render UI widget. The viewport can be set to only cover some of the 
 * target's area, so multiple cameras can render into the widget in different places. By default cameras are instantiated as
 * primary cameras and by default see all scene objects whose visibility settings haven't been changed. By setting a camera 
 * to be seconday it will by default see no scene objects except those Figure objects which explicitly makes themselves 
 * visible to that specific camera. 
 */ 
class Camera
{
public:
	Camera(){}
	virtual ~Camera() {}

	virtual const char* getName() const { return ""; }

	/// Get the aspect ratio of the notional box this camera sees through and shall render to a target
	virtual real getAspectRatio() const { return 0; }
	
	/**
	 * Get the projected ray from a point on the screen, (x,y) are real render target (widget) screen coordinates if `isAbsolute' 
	 * is true, otherwise (x,y) are relative screen proportion values ranging over the unit square. In either case the top left 
	 * corner of the camera's view area is (0,0), the bottom right is (w,h) for view area w-by-h pixels or (1,1) for relative coords.
	 */
	virtual Ray* getProjectedRay(real x, real y, bool isAbsolute=true) const { return NULL; }

	virtual vec3 getPosition() const { return vec3();}
	virtual vec3 getLookAt() const { return vec3();}
	virtual rotator getRotation() const { return rotator(); }

	/// Returns the (x,y) screen coordinate of the vector `pos' as drawn with the current camera configuration.
	virtual vec3 getScreenPosition(vec3 pos) const { return vec3(); }

	/// Returns the world position of screen coordinate (x,y), which is either absolute pixel coordinates or relative screen proportion values (see getProjectedRay())
	virtual vec3 getWorldPosition(real x, real y, bool isAbsolute=true) const 
	{
		Ray *r=getProjectedRay(x,y,isAbsolute);
		vec3 pos=r->getPosition();
		delete r;
		return pos;
	}

	virtual void setPosition(const vec3 &v){}
	virtual void setLookAt(const vec3 &v) {}
	virtual void setUp(const vec3 & v){}
	virtual void setZUp(){}
	virtual void rotate(const rotator & r) {}
	virtual void setRotation(const rotator& r){}

	virtual void setNearClip(real dist) {}
	virtual void setFarClip(real dist) {}
	virtual void setVertFOV(real rads) {}
	virtual void setBGColor(const color & c) {}
	virtual void setAspectRatio(real rat) {}
	virtual void setViewport(real left=0.0f,real top=0.0f,real width=1.0f,real height=1.0f) {}
	virtual void setOrtho(bool isOrtho){}
	virtual void setWireframe(bool isWireframe){}
	virtual void setSecondaryCamera(bool selective){}

	virtual real getVertFOV() const { return 0; }
	
	virtual real getNearClip() const {return 0; }
	virtual real getFarClip() const {return 0; }

	virtual sval getWidth() const { return 0; }
	virtual sval getHeight() const { return 0; }

	virtual bool isPointInViewport(int x, int y) const { return false;}
	
	virtual bool isSecondaryCamera() { return false; }

	/// Create an offscreen texture, render to it, then write the contents to the file `filename', assuming it's extension is for an understood format.
	virtual void renderToFile(const std::string& filename,sval width,sval height, TextureFormat format=TF_RGB24,real stereoOffset=0.0) throw(RenderException) {}
	/// Create an offscreen texture, render to it, then blit the contents to `stream', which must be large enough for data of the given texture format.
	virtual void renderToStream(void* stream,sval width,sval height, TextureFormat format=TF_RGB24,real stereoOffset=0.0) throw(RenderException) {}
	/// Create an offscreen texture, render to it, then blit the contents to the returned Image object, which can then be used to save the image to file.
	virtual Image* renderToImage(sval width,sval height, TextureFormat format=TF_RGB24,real stereoOffset=0.0) throw(RenderException) { return 0; }
};

/**
 * A Figure object is the basic rendering object. It has methods for filling vertex and index data, setting
 * camera visibility, scene position and orientation, and materials.
 */
class Figure
{
public:
	virtual ~Figure(){}

	/// Get the figure's name
	virtual const char* getName() {return "";}
	/// Set the figure's position in world space
	virtual void setPosition(const vec3 &v) {}
	/// Set the figure's scale values
	virtual void setScale(const vec3 &v) {}
	/// Set the figure's rotation
	virtual void setRotation(const rotator& r){}
	/// Set position, rotation, and scale for this figure simultaneously
	virtual void setTransform(const transform &t) { setTransform(t.trans,t.scale,t.rot); }
	/// Set position, rotation, and scale for this figure simultaneously
	virtual void setTransform(const vec3 &trans,const vec3 &scale, const rotator &rot)
	{
		setPosition(trans);
		setRotation(rot);
		setScale(scale);
	}

	/// Get the figure's position in world space
	virtual vec3 getPosition(bool isDerived=false) const { return vec3(); }
	/// Get the figure's scale values
	virtual vec3 getScale(bool isDerived=false) const { return vec3(); }
	/// Get the figure's rotation
	virtual rotator getRotation(bool isDerived=false) const { return rotator(); }
	/// Get the figure's position, scale, and rotation transform
	virtual transform getTransform(bool isDerived=false) const { return transform(getPosition(isDerived),getScale(isDerived),getRotation(isDerived),false); }

	/// Set the figure's material, this must name an existing material 
	virtual void setMaterial(const char* mat) throw(RenderException) {}
	/// Set's the figure's material
	virtual void setMaterial(const Material *mat) throw(RenderException) { setMaterial(mat->getName()); }

	/// Get the figure's material name
	virtual const char* getMaterial() const { return ""; }

	virtual std::pair<vec3,vec3> getAABB() const { return std::pair<vec3,vec3>(vec3(),vec3()); }

	/** 
	 * Fill the vertex information using the given buffers, `ib' may be NULL for point figure types. If `deferFill' is
	 * true then the actual hardware buffers are filled during the next render cycle rather than immediately. In either
	 * case data is filled into local memory buffers first then copied to hardware buffers. This implies that calling this
	 * method is thread-safe if `deferFill' is true or if its implementation does nothing regardless of arguments. 
	 * If `doubleSided' is true and the index buffer defined triangles, create backfaces for triangles with correct normals. 
	 */
	virtual void fillData(const VertexBuffer* vb, const IndexBuffer* ib,bool deferFill=false,bool doubleSided=false) throw(RenderException) {}
	
	/// Sets the figure's visibility
	virtual void setVisible(bool isVisible){}
	/// Returns the figure's visibility state
	virtual bool isVisible() const { return false;}

	/// Returns true if the figure includes transparent elements
	virtual bool isTransparent() const { return false; }
	/// Returns true if the figure is part of the UI overlay rather than an object in space
	virtual bool isOverlay() const { return false; }

	/// Set the transparency state of the figure, this doesn't actually change data but affects how the renderer treates the object
	virtual void setTransparent(bool isTrans){}
	/// Set the overlay state of the figure, this doesn't actually change data but affects how the renderer treates the object
	virtual void setOverlay(bool isOverlay){}

	/// Get the render queue of this figure; queues set rendering order such that figures in lower queues are rendered first
	virtual void setRenderQueue(sval queue){}
	/// Get the figure's render queue
	virtual sval getRenderQueue() const { return 0; }

	/**
	 * Set the visibility for this figure in the given camera, by default a camera can see all figures unless it has 
	 * been designated as a secondary camera, in which case figures must make themselves explicitly visible to it 
	 * using this method. This implies that a figure is by default is visible to all primary cameras. All primary 
	 * cameras are treated the same, so a figure visible to one is visible to all. If `cam' is NULL then visibility 
	 * is set for all cameras, both primary and secondary, to be `isVisible'. 
	 */
	virtual void setCameraVisibility(const Camera* cam, bool isVisible){}

	/// Set the parent of this figure, if `fig' is transformed then the transformation is applied to this figure as well
	virtual void setParent(Figure *fig){}
};

/// This subtype of Figure represents a set of billboards, squares with textures in space which are oriented relative to the camera
class BBSetFigure : public Figure
{
public:
	virtual ~BBSetFigure(){}

	virtual void setDimension(real width, real height){}

	virtual real getWidth() const { return 0;}
	virtual real getHeight() const { return 0;}

	virtual void setUpVector(const vec3& v){}

	virtual int numBillboards() const {return 0;}

	virtual void fillData(const VertexBuffer* vb, const IndexBuffer* ib,bool deferFill=false,bool doubleSided=false) throw(RenderException) {}

	virtual void setBillboardPos(indexval index, const vec3& pos) throw(IndexException) {}
	virtual void setBillboardDir(indexval index, const vec3& dir) throw(IndexException) {}
	virtual void setBillboardColor(indexval index, const color& col) throw(IndexException) {}
};

class TextureVolumeFigure : public Figure
{
public:
	virtual ~TextureVolumeFigure() {}
	
	virtual void setNumPlanes(sval num){}
	virtual sval getNumPlanes() const { return 0; }
	
	virtual void setAlpha(real a) {}
	virtual real getAlpha() const { return 0; }

	virtual void setTexAABB(const vec3& minv, const vec3& maxv) {}

	virtual void setAABB(const vec3& minv, const vec3& maxv) {}
	//virtual void setTexCoordDir(bool invertX, bool invertY, bool invertZ) {}

	virtual vec3 getTexXiPos(vec3 pos) const { return vec3();}

	virtual vec3 getTexXiDir(vec3 pos) const { return vec3();}

	virtual sval getPlaneIntersects(vec3 planept, vec3 planenorm,vec3 buffer[6][2],bool transformPlane=false,bool isXiPoint=false)
	{
		return 0;
	}
};

class GlyphFigure : public Figure
{
public:
	virtual ~GlyphFigure() {}

	virtual void setGlyphScale(vec3 v) {}
	virtual vec3 getGlyphScale() const { return vec3(); }
	virtual void setGlyphName(const std::string& name) {}
	virtual std::string getGlyphName() const {return ""; }
	virtual void addGlyphMesh(const std::string& name,const Vec3Matrix* nodes, const Vec3Matrix* norms, const IndexMatrix* inds) {}
};

class RibbonFigure : public Figure
{
public:
	virtual ~RibbonFigure() {}
	virtual void setOrientation(const vec3& orient) {}
	virtual bool isCameraOriented() const { return true; }
	virtual vec3 getOrientation() const { return vec3(); }

	virtual void setNumRibbons(sval num) {}
	virtual sval numRibbons() const { return 0; }
	virtual sval numNodes(sval ribbon) const throw(IndexException) { return 0; }
	virtual void setMaxNodes(sval num) {}
	virtual sval getMaxNodes() const { return 0; }
	
	virtual void clearRibbons() {}
	virtual void removeRibbon(sval ribbon) throw(IndexException) {}
	virtual void removeNode(sval ribbon) throw(IndexException) {}
	virtual void addNode(sval ribbon,const vec3& pos, const color& col,real width, const rotator& rot=rotator(), real tex=0.0) throw(IndexException) {}
	virtual void setNode(sval ribbon,sval node,const vec3& pos, const color& col,real width, const rotator& rot=rotator(), real tex=0.0) throw(IndexException) {}
	virtual vec3 getNode(sval ribbon,sval node) throw(IndexException) { return vec3(); }
	virtual quadruple<color,real,rotator,real> getNodeProps(sval ribbon,sval node) throw(IndexException) { return quadruple<color,real,rotator,real>(); }
};

class TextFigure : public Figure
{
public:
	virtual ~TextFigure() {}
	virtual void setText(const std::string& text) {}
	virtual void setFont(const std::string& fontname) {}
	virtual void setColor(const color& col) {}
	
	virtual void setVAlign(VAlignType align){}
	virtual void setHAlign(HAlignType align){}
	virtual void setTextHeight(real height){}
	virtual void setSpaceWidth(real width) {}
	
	virtual std::string getText() const { return "";}
	virtual std::string getFont() const { return "";}
	virtual color getColor() const { return color(); }
	
	virtual VAlignType getVAlign() const { return V_CENTER; }
	virtual HAlignType getHAlign() const { return H_CENTER; }
	virtual real getTextHeight() const { return 0; }
	virtual real getSpaceWidth() const { return 0; }
};

/** 
 * Stores configuration values derived from arguments and config files. Values are always stored as strings keyed to
 * (group,name) pairs, where group is the category the value is a member of. Categories may include anything depending
 * on context, `platformID' is the group for per-platform config values with "All" containing default values for all
 * platforms. Other groups include "args" for command line arguments, "vars" for variable specified on the command line,
 * and `RenderParamGroup' containing values for initializing the renderer. Group and name values are NOT case sensitive.
 */
class Config
{
protected:
	typedef std::pair<std::string,std::string> strpair;
	typedef std::map<strpair,std::string> configmap;

	configmap map;

public:
	Config(){}

	void set(const char* group, const char* name, const char* value) { map[getPair(group,name)]=value; }
	void set(const char* name, const char* value) { map[getPair("",name)]=value; }
	bool hasValue(const char* group, const char* name) const { return map.find(getPair(group,name))!=map.end(); }
	bool hasValue(const char* name) const { return hasValue("",name); }
	const char* get(const char* group, const char* name) { return hasValue(group,name) ? map[getPair(group,name)].c_str() : ""; }
	const char* get(const char* name) { return get("",name); }

	std::string toString()
	{
		std::ostringstream out;
		for(configmap::const_iterator i=map.begin();i!=map.end();i++)
			out << "(" <<(*i).first.first << ", " << (*i).first.second << ") = " << (*i).second << std::endl;

		return out.str();
	}

	friend std::ostream& operator << (std::ostream &out, const Config *c)
	{
		for(configmap::const_iterator i=c->map.begin();i!=c->map.end();i++)
			out << "(" <<(*i).first.first << ", " << (*i).first.second << ") = " << (*i).second << std::endl;

		return out;
	}
	
private:
	strpair getPair(const char* group, const char* name) const
	{
		std::string sgroup=group,sname=name;
		std::transform(sgroup.begin(), sgroup.end(), sgroup.begin(), ::tolower);
		std::transform(sname.begin(), sname.end(), sname.begin(), ::tolower);
		return strpair(sgroup,sname);
	}
};

/**
 * This class represents the rendering scene and the factory for all render-related objects including cameras, lights, figures, and materials. It also
 * is responsible for loading textures and other properties (more to be added later). Only one instance should ever exist which is created by the
 * RenderAdapter instance. None of the methods of this type should be considered thread-safe.
 */
class RenderScene
{
	bool renderHighQuality;
	bool alwaysHighQuality;

public:
	RenderScene() : renderHighQuality(false), alwaysHighQuality(false) {}

	virtual ~RenderScene() {}

	/**
	 * Create a camera object with the given name covering the proportionate area of the 3D window. The top left corner of
	 * the 3D window is (0.0,0.0) and its dimensions are (1.0,1.0), which are the default values of the left, top, width, and
	 * height arguments. 
	 */
	virtual Camera* createCamera(const char* name,real left=0.0f,real top=0.0f,real width=1.0f,real height=1.0f) throw(RenderException) { return NULL; }
	
	/// Set the scene ambient light to the given color value.
	virtual void setAmbientLight(const color & c) {}

	/// Add a directory to search for resources in.
	virtual void addResourceDir(const char* dir) {}
	
	/// Onces all resource directories are added, initialize the internal resource system.
	virtual void initializeResources() {}

	/// Create a material object of the given name.
	virtual Material* createMaterial(const char* name) throw(RenderException) {return NULL;}

	/// Create a figure of the given name, with material named by `mat', and type `type'.
	virtual Figure* createFigure(const char* name, const char* mat,FigureType type) throw(RenderException) {return NULL;}

	/// Create a light object.
	virtual Light* createLight() throw(RenderException) { return NULL; }

	/// Load an image from the given filename.
	virtual Image* loadImageFile(const std::string &filename) throw(RenderException) { return NULL; }

	/// Create a 3D texture with the given name, dimensions, and format. Textures are always 3D but a `depth' value of 1 produces the equivalent of a 2D texture.
	virtual Texture* createTexture(const char* name,sval width, sval height, sval depth, TextureFormat format) throw(RenderException) { return NULL; }

	/// Load a texture of the given name from the image absolute path filename.
	virtual Texture* loadTextureFile(const char* name,const char* absFilename) throw(RenderException) { return NULL; }
	
	/// Load a GPU program (shader) of the given name, type, and language (ie. Cg).
	virtual GPUProgram* createGPUProgram(const char* name,ProgramType ptype,const char* language) throw(RenderException) { return NULL; }

	/// Save a screenshot to the given filename taken from the given camera, or of the whole 3D window if this isn't provided.
	virtual void saveScreenshot(const char* filename,Camera* c=NULL,int width=0,int height=0,real stereoOffset=0.0,TextureFormat tf=TF_RGB24) throw(RenderException) {}

	/// Returns the Config object used to define properties for the scene.
	virtual Config* getConfig() const {return NULL; }

	/// Log a message to the renderer log file.
	virtual void logMessage(const char* msg){}
	
	/// Set the background skybox to the given color if `enabled' is true, otherwise disable it.
	virtual void setBGObject(color col,bool enabled){}

	/// Set whether rendering should be done using high quality passes or not
	void setRenderHighQuality(bool val) { renderHighQuality=val; }
	
	/// Set whether to force high quality rendering 
	void setAlwaysHighQuality(bool val) { alwaysHighQuality=val; }

	/// Returns whether the next render operation will be in high quality mode.
	bool getRenderHighQuality() const { return renderHighQuality || alwaysHighQuality;}
	
	/// Returns whether to always render in high quality mode.
	bool getAlwaysHighQuality() const  { return alwaysHighQuality; }
};

/**
 * This class represents the bridge between the rendering engine and the windowing toolkit. It is instantiated for the 
 * windowing object that will be the target for rendering. It's main purpose is to collect into one place the code for 
 * creating and resizing the render window and processing paint events. This also allows the windowing class to be defined 
 * without using headers for the rendering engine.
 * 
 * A RenderAdapter type is instantiated through getRenderAdapter() which is implemented by the specific renderer being 
 * used, thus it returns a specialized subtype specific to that renderer. The Config object passed as the argument is 
 * retained and used as the source of parameter info needed to instantiate the renderer. Once the object is created, 
 * createWindow() must be called after the host UI widget has been created so that the parameters identifying the window 
 * have been set in the Config object. These parameters are necessary since the renderer has to bind to a  place to render 
 * into. Once this has been done and the widget is visible, only then can getRenderScene() be called to create the 
 * RenderScene object needed to interact with the renderer. Whenever the widget resizes resize() must be called with the 
 * new size as arguments. When the widget receives a paint event, paint() is called to cause a redraw of the scene by the 
 * renderer.
 *
 * The function getRenderAdapter() and all the methods of this type are not thread-safe and should only be called by the
 * windowing system's message pump (ie. main) thread.
 * 
 * The parameters to pass to the Config object are specific to the platform and renderer being used, but must be stored in 
 * the RenderParamGroup config group. For Ogre these are the following named values:
 * 
 *   Windows: parent window ID number in "parentWindowHandle"
 *   Linux:   D:S:W in "parentWindowHandle" where D is the display number, S the screen number, and W the window ID number
 *   OSX:     window ID number in "externalWindowHandle"
 */
class RenderAdapter
{
public:
	virtual ~RenderAdapter(){}

	virtual u64 createWindow(int width, int height)  throw(RenderException) { return 0; }
	virtual void paint(){}
	virtual void resize(int x, int y,int width, int height){}
	virtual RenderScene* getRenderScene() { return NULL; }
};

/**
 * Returns an instance of the RenderAdapter specific to the rendering engine being used. This is not implemented in 
 * Rendertypes.[h,cpp] but in the engine itself. The `config' object is for passing in parameters to the adapter.
 */
RenderAdapter* getRenderAdapter(Config* config) throw(RenderException);

/*****************************************************************************************************************************/
/* Algorithms */
/*****************************************************************************************************************************/

template<typename T,typename V> void setMatrixMinMax(Matrix<T>* mat,const V& minv,const V& maxv)
{
	std::ostringstream os;
	os << V(minv);
	mat->meta("min",os.str().c_str());
	os.str("");
	os << V(maxv);
	mat->meta("max",os.str().c_str());
}

/// Partial templates for converting strings to primitives/vec3
template<typename T> struct StrConvert { static T conv(const char* str) { return T(); } };
template<> struct StrConvert<real> { static real conv(const char* str) { return atof(str); } };
template<> struct StrConvert<indexval> { static indexval conv(const char* str) { return atol(str); } };

/// Partial templates for converting a line of text into a list of primitives/vec3
template<typename T> struct ParseLine 
{ 
	static void parse(const char* line,sval numvals,T* list) 
	{
		char *buf=new char[strlen(line)+1];
		strcpy(buf,line);
			
		char* p=strtok(buf," \t\r\n");
	
		for(sval x=0;x<numvals && p;x++){
			list[x]=StrConvert<T>::conv(p);
			p=strtok(NULL," \t\r\n");
		}
			
		delete buf;
	} 
};

/// vec3 specific case to handle turning 3 parsed values into 1 object
template<> struct ParseLine<vec3>
{ 
	static void parse(const char* line,sval numvals,vec3* list) 
	{
		char *buf=new char[strlen(line)+1];
		strcpy(buf,line);
			
		char* p=strtok(buf," \t\r\n");
	
		for(sval i=0;i<numvals && p;i++){
			real x=StrConvert<real>::conv(p);
			p=strtok(NULL," \t\r\n");
			real y=(p ? StrConvert<real>::conv(p) : 0);
			p=strtok(NULL," \t\r\n");
			real z=(p ? StrConvert<real>::conv(p) : 0);
			p=strtok(NULL," \t\r\n");
			list[i]=vec3(x,y,z);
		}
			
		delete buf;
	} 
};

/// Reads the text file into the given matrix, ignoring the header of integers and using the dimensions of `mat' to determine line width
template<typename T>
void readTextFileMatrix(const std::string & filename, sval numHeaders, Matrix<T>* mat)
{
	std::ifstream in(filename.c_str());

	if(!in)
		return;

	std::string line;
	sval numvals=sval(mat->m());
	T* entry=new T[numvals];

	if(numHeaders>0){
		sval* header=new sval[numHeaders];
		std::getline(in,line);	
		ParseLine<sval>::parse(line.c_str(),numHeaders,header);
		delete header;
	}

	while(std::getline(in,line)){		
		if(line.find_first_not_of(" \n\t\r")==std::string::npos)
			continue;

		ParseLine<T>::parse(line.c_str(),numvals,entry);

		mat->append(entry[0]);
		sval pos=mat->n()-1;
		for(sval x=1;x<numvals;x++)
			mat->at(pos,x)=entry[x];
	}

	delete entry;
}


/// Fill a given RealMatrix with data from the given byte stream which contains values of various types
//template<typename T> void convertStreamToRealMatrix(const T* stream, RealMatrix* mat);
template<typename T>
void convertStreamToRealMatrix(const T* stream, RealMatrix* mat)
{
	T minval=stream[0];
	T maxval=minval;
	sval mn=mat->n(),mm=mat->m();

	for(sval n=0;n<mn;n++)
		for(sval m=0;m<mm;m++){
			T val=stream[n*mm+m]; // totally unsafe if stream is too short
			minval=_min(val,minval);
			maxval=_max(val,maxval);

			mat->at(n,m)=val;
		}

	setMatrixMinMax<real,real>(mat,minval,maxval);
}

void convertUByteStreamToRealMatrix(const char* stream, RealMatrix* mat);
void convertUShortStreamToRealMatrix(const char* stream, RealMatrix* mat);
void convertByteStreamToRealMatrix(const char* stream, RealMatrix* mat);
void convertShortStreamToRealMatrix(const char* stream, RealMatrix* mat);
void convertUIntStreamToRealMatrix(const char* stream, RealMatrix* mat);
void convertIntStreamToRealMatrix(const char* stream, RealMatrix* mat);
void convertFloatStreamToRealMatrix(const char* stream, RealMatrix* mat);
void convertRealStreamToRealMatrix(const char* stream, RealMatrix* mat);
//void convertRGBA32StreamToRealMatrix(const u8* stream, RealMatrix* mat);

//RealMatrix* readImageFile(const std::string& filename);

std::pair<vec3,vec3> calculateBoundBox(const Vec3Matrix* mat);


/**
 * Calculates where the edges of the triangle (a,b,c) pass through the plane defined by `planept' and `planenorm'. The three
 * values refer to the edges a-b, a-c, and b-c respectively. If a value is positive then the first node (a or b) is above the
 * plane, otherwise below. The value is the proportionate distance from the first node to the second where the intersection
 * takes place, so if the first value is 0.25 then a is above the plane and the intersection is at point a+(b-a)*0.25.
 */
realtriple calculateTriPlaneSlice(const vec3& planept, const vec3& planenorm, const vec3& a, const vec3& b, const vec3& c);
real calculateLinePlaneSlice(const vec3& planept, const vec3& planenorm, const vec3& a, const vec3& b);

void calculateTetValueIntersects(real val, real a, real b, real c, real d, real* results);

sval calculateHexValueIntersects(real val,const real* vals,intersect* results);

/// Linear Nodal Lagrange tetrahedron basis function, fills in `coeffs' for the given xi value, `coeffs' must be 4 long.
void basis_Tet1NL(real xi0, real xi1, real xi2, real* coeffs);

/// Linear Nodal Lagrange hexahedron basis function, fills in `coeffs' for the given xi value, `coeffs' must be 8 long.
void basis_Hex1NL(real xi0, real xi1, real xi2, real* coeffs);

real basis_n_NURBS(sval ctrlpt,sval degree, real xi,const RealMatrix *knots);

void basis_NURBS_default(real u, real v, real w,sval ul, sval vl, sval wl, sval udegree, sval vdegree, sval wdegree,real* coeffs);

/// Produces the 4 coefficients for a Catmull-Rom spline in [value 1, value 2, derivative 1, derivative 2] orderings in `coeffs'.
void catmullRomSpline(real t, real* coeffs);

/**
 * This computes the determinant of a 4x4 matrix in the following way:
 * 
 *     |a b c d|
 * DET |e f g h|
 *     |i j k l|
 *     |m n o p|
 *         =
 * l*o*b*e - k*p*b*e - l*n*c*e + j*p*c*e + k*n*d*e - j*o*d*e - a*l*o*f + a*k*p*f + l*m*c*f - k*m*d*f + a*l*n*g - a*j*p*g - 
 * l*m*b*g + j*m*d*g - a*k*n*h + a*j*o*h + k*m*b*h - j*m*c*h - p*c*f*i + o*d*f*i + p*b*g*i - n*d*g*i - o*b*h*i + n*c*h*i
 */
real mat4Det(real a, real b, real c, real d, real e, real f, real g, real h, real i, real j, real k, real l, real m, real n, real o, real p);

/// Returns true if `pt' is in the tet defined by (n1,n2,n3,n4).
bool pointInTet(vec3 pt, vec3 n1, vec3 n2, vec3 n3, vec3 n4);

/// Returns true if `pt' is in the hex defined by (n1-n8)
bool pointInHex(vec3 pt, vec3 n1, vec3 n2, vec3 n3, vec3 n4, vec3 n5, vec3 n6, vec3 n7, vec3 n8);

/// Returns the volume of the linear tetrahedron defined by (a,b,c,d), the volume will be negative for an inverted tet.
inline float calculateTetVolume(vec3 a, vec3 b, vec3 c, vec3 d)
{
	return -mat4Det(a.x(),b.x(),c.x(),d.x(),a.y(),b.y(),c.y(),d.y(),a.z(),b.z(),c.z(),d.z(),1,1,1,1)/6.0;
}

/**
 * This determines the xi value for point `pt' within the tetrahedron defined by (n1,n2,n3,n4). This relies on considering
 * the tet to define its own coordinate space with axes n2-n1, n3-n1, and n4-n1, and where pt-n1 is a point in this space
 * stated as the sum of multiples of these axes. In this conception the xi coordinate is the set of multipliers, thus:
 * 
 *    pt     =           A           *   xi
 * =
 *  | n-n1 | = | n2-n1 n3-n1 n4-n1 | * | xi  |
 * = 
 *  | x-x1 |   | x2-x1 x3-x1 x4-x1 |   | xi1 |
 *  | y-y1 | = | y2-y1 y3-y1 y4-y1 | * | xi2 | 
 *  | z-z1 |   | z2-z1 z3-z1 z4-z1 |   | xi3 |
 *
 * Thus xi = X * A^-1
 * 
 *  | x2-x1 x3-x1 x4-x1 |-1             | (z4-z1)(y3-y1)-(z3-z1)(y4-y1) (z3-z1)(x4-x1)-(z4-z1)(x3-x1) (y4-y1)(x3-x1)-(y3-y1)(x4-x1) |
 *  | y2-y1 y3-y1 y4-y1 |    =  1/DET * | (z2-z1)(y4-y1)-(z4-z1)(y2-y1) (z4-z1)(x2-x1)-(z2-z1)(x4-x1) (y2-y1)(x4-x1)-(y4-y1)(x2-x1) |
 *  | z2-z1 z3-z1 z4-z1 |               | (z3-z1)(y2-y1)-(z2-z1)(y3-y1) (z2-z1)(x3-x1)-(z3-z1)(x2-x1) (y3-y1)(x2-x1)-(y2-y1)(x3-x1) |
 * 
 *   with DET  =  (x2-x1)((z4-z1)(y3-y1)-(z3-z1)(y4-y1))-(y2-y1)((z4-z1)(x3-x1)-(z3-z1)(x4-x1))+(z2-z1)((y4-y1)(x3-x1)-(y3-y1)(x4-x1))
 */
vec3 pointSearchLinTet(vec3 pt, vec3 n1, vec3 n2, vec3 n3, vec3 n4);

/**
 * This determines the xi value for the point `pt' within the hexahedron defined by (n1-n8). The algorithm embeds 5 tets within the hex
 * and performs point search on these. This gives an exacting solution for hexes defined with coplanar faces; non-coplanar hexes have 
 * curvature which is not handled well by the tet division.
 */
vec3 pointSearchLinHex(vec3 pt, vec3 n1, vec3 n2, vec3 n3, vec3 n4, vec3 n5, vec3 n6, vec3 n7, vec3 n8);

template<typename T>
void cubicInterpMatrices(real t,const Matrix<T>* v1,const Matrix<T>* v2,const Matrix<T>* m1,const Matrix<T>* m2,const Matrix<T>* result)
{
	sval rows=_min(v1->n(),_min(v2->n(),_min(m1->n(),_min(m2->n(),result->n()))));
	sval cols=_min(v1->m(),_min(v2->m(),_min(m1->m(),_min(m2->m(),result->m()))));
	real coeffs[4];
	catmullRomSpline(t,coeffs);

	for(sval i=0;i<rows;i++)
		for(sval j=0;j<cols;j++){
			T a=coeffs[0]*v1->at(i,j);
			T b=coeffs[1]*v2->at(i,j);
			T c=coeffs[2]*m1->at(i,j);
			T d=coeffs[3]*m2->at(i,j);
			result->at(i,j)=a+b+c+d;
		}
}

/// Returns the bounding box (minx,miny,maxx,maxy) in matrix coordinates containing all values in `mat' greater than `threshold'.
template<typename T>
quadruple<int,int,int,int> calculateBoundSquare(const Matrix<T>* const mat,const T& threshold)
{
	int minx=-1,maxx=-1,miny=-1,maxy=-1;

	sval rows=mat->n();
	sval cols=mat->m();

	for(sval i=0;i<rows && miny<0;i++)
		for(sval j=0;j<cols;j++)
			if(mat->at(i,j)>threshold){
				miny=int(i);
				break;
			}

	for(sval i=rows;i>0 && maxy<0;i--)
		for(sval j=0;j<cols;j++)
			if(mat->at(i-1,j)>threshold){
				maxy=int(i-1);
				break;
			}

	for(sval j=0;j<cols && minx<0;j++)
		for(sval i=0;i<rows;i++)
			if(mat->at(i,j)>threshold){
				minx=int(j);
				break;
			}

	for(sval j=cols;j>0 && maxx<0;j--)
		for(sval i=0;i<rows;i++)
			if(mat->at(i,j-1)>threshold){
				maxx=int(j-1);
				break;
			}

	return quadruple<int,int,int,int>(minx,miny,maxx,maxy);
}

template<typename T>
sval countValuesInRange(const Matrix<T> *mat, const T& minv, const T& maxv)
{
	sval count=0, rows=mat->n(), cols=mat->m();

	for(sval i=0;i<rows;i++)
		for(sval j=0;j<cols;j++){
			sval val=mat->at(i,j);
			if(val>=minv && val<=maxv)
				count++;
		}

	return count;
}

template<typename T>
std::vector<vec3> findBoundaryPoints(const Matrix<T>* mat, const T& threshold)
{
	std::vector<vec3> result;
	
	sval rows=mat->n();
	sval cols=mat->m();
	
	for(sval i=0;i<rows;i++)
		for(sval j=0;j<cols;j++){
			T val=mat->atc(i,j);
			if(val<threshold)
				continue;
			
			bool allInternal=true;
			for(sval n=_max<sval>(0,i-1);allInternal && n<_min(rows,i+1);n++)
				for(sval m=_max<sval>(0,j-1);allInternal && m<_min(cols,j+1);m++)
					if(n!=i || m!=j)
						allInternal=allInternal && mat->getAt(n,m)>=threshold;
				
			if(!allInternal)
				result.push_back(vec3(i,j,0));
		}
		
	return result;
}

template<typename T>
T sumMatrix(const Matrix<T> *mat)
{
	T result=T();
	sval rows=mat->n();
	sval cols=mat->m();
	
	for(sval i=0;i<rows;i++)
		for(sval j=0;j<cols;j++)
			result+=mat->atc(i,j);

	return result;
}

template<typename T>
std::pair<T,T> minmaxMatrix(const Matrix<T>* mat)
{
	std::pair<T,T> result(mat->atc(0,0),mat->atc(0,0));
	sval rows=mat->n();
	sval cols=mat->m();

	for(sval i=0;i<rows;i++)
		for(sval j=0;j<cols;j++){
			T val=mat->atc(i,j);
			if(val<result.first)
				result.first=val;
			else if(val>result.second)
				result.second=val;
		}

	return result;
}

template<typename T>
T bilerpMatrix(const Matrix<T> *mat,real x, real y) 
{
	if(x<0.0 || x>1.0 || y<0.0 || y>1.0)
		return T();
		
	x*=mat->m()-1;
	y*=mat->n()-1;
		
	sval sx=(sval)floor(x);
	sval sy=(sval)floor(y);

	real dx=x-sx;
	real dy=y-sy;
	real dx1=1.0-dx;
	real dy1=1.0-dy;

	return dx*(dy*mat->atc(sy+1,sx+1)+dy1*mat->atc(sy,sx+1)) + dx1*(dy*mat->atc(sy+1,sx)+dy1*mat->atc(sy,sx));
}

/** 
 * Trilinearly interpolate between `mat1' and `mat2', where `v1' is a xi point on `mat1' and `v2' is a xi point on `mat2'.
 *
 * The x and y components of the two points are interpreted as xi values on their respective planes. A value is derived
 * from each through bilinear interpolation. The z components are interpreted as heights from the planes, these are used
 * to linearly interpolate between the two interpolated points. 
 */
template<typename T>
T trilerpMatrices(const Matrix<T>* mat1, const Matrix<T>* mat2, vec3 v1, vec3 v2)
{
	T val1=bilerpMatrix<T>(mat1,v1.x(),v1.y());
	T val2=bilerpMatrix<T>(mat2,v2.x(),v2.y());
	
	real absz=fabs(v1.z());
	real lerpval=lerpXi<real>(absz,0,absz+fabs(v2.z()));
	
	return lerp(lerpval,val1,val2);
}

/**
 * Computes the xi coordinate of `pos' on the plane defined by `planepos' as the minimum corner, `orientinv' as the 
 * inverse of is orientation, and `dimvec' as its (X,Y) scale factor (ie. quad dimensions). The result contains the
 * 2D xi coordinate 
 */
inline vec3 getPlaneXi(const vec3& pos, const vec3& planepos, const rotator& orientinv, const vec3& dimvec)
{
	return (orientinv*(pos-planepos))/vec3(dimvec.x(),dimvec.y(),1);
}

/**
 * Interpolate the data from the image volume defined by `stack' into the image `out'. The volume `stack' must be defined in a bottom-up ordering. The transform
 * `stacktransinv' represents the inverse transform for the image stack, and `outtrans' is the transform for the image `out'.
 */
void interpolateImageStack(const std::vector<RealMatrix*>& stack,const transform& stacktransinv,RealMatrix *out,const transform& outtrans);

/**
 * Sample the value of the image stack at the image coordinate `pt', which must be in the unit cube otherwise 0 is returned.
 */
real getImageStackValue(const std::vector<RealMatrix*>& stack,const vec3& pos);

void calculateImageHistogram(const RealMatrix* img, RealMatrix* hist, i32 minv); 

/** 
 * Calculate the normals for triangles defined by the `nodes' array and indices `inds'. This requires that `nodes' be 
 * `numnodes' in length and `inds' be of `numinds'*3 in length where each triangle is indexed by triples of indices in 
 * `nodes'. Returns a fresh array of length `numnodes' with a normal for each node.
 */
vec3* calculateTriNorms(vec3* nodes, sval numnodes, indexval* inds, sval numinds);

} // namespace RenderTypes
#endif // RENDERTYPES_H
