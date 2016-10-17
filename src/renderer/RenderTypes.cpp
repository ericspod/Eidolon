/*
 * Eidolon Biomedical Framework
 * Copyright (C) 2016 Eric Kerfoot, King's College London, all rights reserved
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

#include "RenderTypes.h"

namespace RenderTypes {

std::string shmdir="";

void initSharedDir(const std::string& path)
{
	if(path.length()>0)
		shmdir=path;

#ifdef __APPLE__
	if(path.length()>0){
		mkdir(path.c_str(),S_IRWXU);
		setenv("PARENTPID",getPIDStr().c_str(),1);
	}
#endif
}

std::string getSharedDir()
{
	return shmdir;
}

void addShared(const std::string& name)
{
#ifdef __APPLE__
	char filename[1030];
	sprintf(filename,"%s/%s",shmdir.c_str(),name.c_str());
	sval count=0;
	
	if(access(filename,F_OK)!=0){
		std::ofstream out(filename);
		if(out){
			out << getenv("PARENTPID");
			out.close();
		}
	}
#endif	
}

void unlinkShared(const std::string& name)
{
#ifndef WIN32
	shm_unlink(name.c_str());
#endif
}


#ifdef WIN32
std::string formatLastErrorMsg()
{
	DWORD dw = GetLastError();
	DWORD dwFlags=FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS;
	LPVOID lpMsgBuf;
	FormatMessage(dwFlags, NULL, dw, MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT), (LPTSTR) &lpMsgBuf, 0, NULL);

	int length = ::WideCharToMultiByte (CP_ACP, WC_COMPOSITECHECK, (LPCWSTR)lpMsgBuf, -1, NULL, 0,  NULL, NULL);
	char* buff=new char[(length+1)*2];
	::WideCharToMultiByte(CP_ACP, NULL,(LPCWSTR)lpMsgBuf,length,buff,(length+1)*2,'\0',NULL);

	std::string msg(buff);
	LocalFree(lpMsgBuf);
	delete buff;

	return msg;
}
#endif

void readBinaryFileToBuff(const char* filename,size_t offset,void* dest,size_t len) throw(MemException)
{
#ifdef WIN32
	std::ostringstream out;
#ifdef UNICODE
	wchar_t namebuff[1024];
	::MultiByteToWideChar(CP_ACP, NULL,filename, -1, namebuff,int(strlen(filename)+1));
#else
	const char* namebuff=filename;
#endif

	HANDLE file = CreateFile(namebuff, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);

	if(file == INVALID_HANDLE_VALUE){
		out << "Failed to open file " << filename << ": " << formatLastErrorMsg();
		throw MemException(out.str());
	}

	DWORD size=GetFileSize(file,NULL);
	HANDLE mapFile=CreateFileMapping(file,NULL,PAGE_READONLY,0,size,NULL);

	if(mapFile == INVALID_HANDLE_VALUE){
		CloseHandle(file);
		out << "Failed to create file mapping for " << filename << ": " << formatLastErrorMsg();
		throw MemException(out.str());
	}

	char* ptr=(char*)MapViewOfFile(mapFile,FILE_MAP_READ,0,0,0);

	if(!ptr){
		CloseHandle(mapFile);
		CloseHandle(file);
		out << "Unable to map view of file " << filename << ": " << formatLastErrorMsg();
		throw MemException(out.str());
	}

	memcpy(dest,ptr+offset,len);

	UnmapViewOfFile(ptr);
	CloseHandle(mapFile);
	CloseHandle(file);
#else
	struct stat info;
	int fd=open(filename,O_RDONLY);
	fstat(fd,&info);

	char* map=(char*)mmap(0, info.st_size, PROT_READ, MAP_SHARED, fd, 0);

	if(map==MAP_FAILED)
		throw MemException("Failed to mmap file");

	memcpy(dest,map+offset,len);

	close(fd);

	if(munmap(map,len))
		throw MemException("Failed to munmap file");
#endif
}

void storeBufftoBinaryFile(const char* filename,void* src,size_t srcsize,int* header, size_t headerlen) throw(MemException)
{
#ifdef WIN32
	std::ostringstream out;
#ifdef UNICODE
	wchar_t namebuff[1024];

	::MultiByteToWideChar(CP_ACP, NULL,filename, -1, namebuff,int(strlen(filename)+1));
#else
	const char* namebuff=filename;
#endif
	HANDLE file = CreateFile(namebuff, GENERIC_WRITE|GENERIC_READ, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);

	if(file == INVALID_HANDLE_VALUE){
		out << "Failed to open/create file " << filename << ": " << formatLastErrorMsg();
		throw MemException(out.str());
	}

	DWORD totalsize=DWORD(srcsize+headerlen*sizeof(int));

	//SetFilePointer(file,totalsize-1,NULL,0);
	//WriteFile(file,"",1,NULL,NULL);

	HANDLE mapFile=CreateFileMapping(file,NULL,PAGE_READWRITE,0,totalsize,NULL);

	if(mapFile == INVALID_HANDLE_VALUE){
		CloseHandle(file);
		out << "Failed to create file mapping for " << filename << ": " << formatLastErrorMsg();
		throw MemException(out.str());
	}

	char* map=(char*)MapViewOfFile(mapFile,FILE_MAP_READ|FILE_MAP_WRITE,0,0,0);

	if(!map){
		CloseHandle(mapFile);
		CloseHandle(file);
		out << "Unable to map view of file " << filename << ": " << formatLastErrorMsg();
		throw MemException(out.str());
	}

	if(headerlen>0)
		memcpy(map,header,headerlen*sizeof(int));

	memcpy(map+headerlen*sizeof(int),src,srcsize);

	UnmapViewOfFile(map);
	CloseHandle(mapFile);
	CloseHandle(file);
#else
	size_t totalsize=srcsize+headerlen*sizeof(int);
	int fd=open(filename,O_RDWR|O_CREAT|O_TRUNC,(mode_t)0600);

	lseek(fd,totalsize-1,SEEK_SET);
	ssize_t s=write(fd,"",1);

	char* map=(char*)mmap(0, totalsize, PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0);
	close(fd);

	if(map==MAP_FAILED)
		throw MemException("Failed to mmap file");

	if(headerlen>0)
		memcpy(map,header,headerlen*sizeof(int));

	memcpy(map+headerlen*sizeof(int),src,srcsize);

	if(munmap(map,totalsize))
		throw MemException("Failed to munmap file");
#endif
}

/*template<typename T>
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
}*/

void convertUByteStreamToRealMatrix(const char* stream, RealMatrix* mat)
{
	convertStreamToRealMatrix((const unsigned char*)stream,mat);
}

void convertUShortStreamToRealMatrix(const char* stream, RealMatrix* mat)
{
	convertStreamToRealMatrix((const unsigned short*)stream,mat);
}

void convertByteStreamToRealMatrix(const char* stream, RealMatrix* mat)
{
	convertStreamToRealMatrix((const char*)stream,mat);
}

void convertShortStreamToRealMatrix(const char* stream, RealMatrix* mat)
{
	convertStreamToRealMatrix((const short*)stream,mat);
}

void convertUIntStreamToRealMatrix(const char* stream, RealMatrix* mat)
{
	convertStreamToRealMatrix((const u32*)stream,mat);
}

void convertIntStreamToRealMatrix(const char* stream, RealMatrix* mat)
{
	convertStreamToRealMatrix((const i32*)stream,mat);
}

void convertFloatStreamToRealMatrix(const char* stream, RealMatrix* mat)
{
	convertStreamToRealMatrix((const float*)stream,mat);
}

void convertRealStreamToRealMatrix(const char* stream, RealMatrix* mat)
{
	convertStreamToRealMatrix<real>((const double*)stream,mat);
}

std::pair<vec3,vec3> calculateBoundBox(const Vec3Matrix* mat)
{
	vec3 minv,maxv;

	if(mat && mat->n()>0){
		minv=mat->getAt(0);
		maxv=mat->getAt(0);

		sval rows=mat->n();

		for(sval i=1;i<rows;i++){
			vec3 pos=mat->getAt(i);
			minv.setMinVals(pos);
			maxv.setMaxVals(pos);
		}
	}

	return std::pair<vec3,vec3>(minv,maxv);
}

void basis_Tet1NL(real xi0, real xi1, real xi2, real* coeffs)
{
	coeffs[0]=1.0-xi0-xi1-xi2;
	coeffs[1]=xi0;
	coeffs[2]=xi1;
	coeffs[3]=xi2;
}

void basis_Hex1NL(real xi0, real xi1, real xi2, real* coeffs)
{
	real xi012=xi0*xi1*xi2;
	real xi12=xi1*xi2;
	real xi01=xi0*xi1;
	real xi02=xi0*xi2;

	coeffs[0]=1.0-xi0-xi1-xi2+xi01+xi02+xi12-xi012;
	coeffs[1]=xi0-xi01-xi02+xi012;
	coeffs[2]=xi1-xi01-xi12+xi012;
	coeffs[3]=xi01-xi012;
	coeffs[4]=xi2-xi02-xi12+xi012;
	coeffs[5]=xi02-xi012;
	coeffs[6]=xi12-xi012;
	coeffs[7]=xi012;
}

real basis_n_NURBS(sval ctrlpt,sval degree, real xi,const RealMatrix* knots)
{
	real pt1=knots->at(ctrlpt), pt2=knots->at(ctrlpt+1);

	if(degree==0)
		return (pt1<=xi && xi<=pt2) ? 1.0 : 0.0;

	real pt3=knots->at(ctrlpt+degree), pt4=knots->at(ctrlpt+degree+1);

	real nn1=xi-pt1, dd1=pt3-pt1;
	real f=fabs(dd1)<0.0000001 ? 0 : nn1/dd1;

	real nn2=pt4-xi, dd2=pt4-pt2;
	real g=fabs(dd2)<0.0000001 ? 0 : nn2/dd2;

	real b1=basis_n_NURBS(ctrlpt,degree-1,xi,knots);
	real b2=basis_n_NURBS(ctrlpt+1,degree-1,xi,knots);

	return (f*b1)+(g*b2);
}

std::map<std::pair<sval,sval>,RealMatrix*> defaultKnots;

RealMatrix* getDefaultKnotMat(sval length,sval degree)
{
	std::pair<sval,sval> index(length,degree);

	if(defaultKnots.find(index)==defaultKnots.end()){
		RealMatrix *mat=new RealMatrix("knots",0);

		for(real i=0;i<1.0;i+=1.0/(length+degree))
			mat->append(i);

		mat->append(1.0);
		defaultKnots[index]=mat;
	}

	return defaultKnots[index];
}

real scaleXiMat(real xi, sval degree,RealMatrix* knots)
{
	return lerp(xi,knots->at(degree),knots->at(knots->n()-degree-1));
}

void basis_NURBS_default(real u, real v, real w,sval ul, sval vl, sval wl, sval udegree, sval vdegree, sval wdegree,real* coeffs)
{
	RealMatrix *uknots=getDefaultKnotMat(ul,udegree);
	RealMatrix *vknots=getDefaultKnotMat(vl,vdegree);
	RealMatrix *wknots=getDefaultKnotMat(wl,wdegree);

	u=scaleXiMat(u,udegree,uknots);
	v=scaleXiMat(v,vdegree,vknots);
	w=scaleXiMat(w,wdegree,wknots);

	real denom=0;

	RealMatrix ub("ub",ul);
	RealMatrix vb("vb",vl);
	RealMatrix wb("wb",wl);

	for(sval i=0;i<ul;i++)
		ub[i]=basis_n_NURBS(i,udegree,u,uknots);

	for(sval j=0;j<vl;j++)
		vb[j]=basis_n_NURBS(j,vdegree,v,vknots);

	for(sval k=0;k<wl;k++)
		wb[k]=basis_n_NURBS(k,wdegree,w,wknots);

	for(sval k=0;k<wl;k++)
		for(sval j=0;j<vl;j++)
			for(sval i=0;i<ul;i++){
				sval index=i+(j*ul)+(k*ul*vl);
				real b=ub[i]*vb[j]*wb[k];
				coeffs[index]=b;
				denom+=b;
			}

	if(denom!=0)
		for(sval i=0;i<ul*vl*wl;i++)
			coeffs[i]/=denom;
}

void catmullRomSpline(real t, real* coeffs)
{
	real t2=t*t;
	real t3=t2*t;
	real t3_05=t3*0.5;
	real t3_15=t3*1.5;
	real t_05=t*0.5;
	
	coeffs[0]=t3_15-2.5*t2+1;
	coeffs[1]=2*t2+t_05-t3_15;
	coeffs[2]=t2-t_05-t3_05;
	coeffs[3]=t3_05-0.5*t2;
}

real mat4Det(real a, real b, real c, real d, real e, real f, real g, real h, real i, real j, real k, real l, real m, real n, real o, real p)
{
	// each of these products occurs twice in the above expression, so they can be factored out to half the number of multiplication ops
	real ob = o * b, le = l * e, kb = k * b, pe = p * e, nc = n * c, jc = j * c, kn = k * n, de = d * e, jo = j * o, al = a * l, of = o * f,
		cf = c * f, lm = l * m, ap = a * p, kf = k * f, md = m * d, ng = n * g, jg = j * g, bg = b * g, ah = a * h, mh = m * h, pi = p * i,
		di = d * i, hi = h * i;

	return le * ob - kb * pe - le * nc + jc * pe + kn * de - jo * de - al * of + ap * kf + lm * cf - kf * md + al * ng - ap * jg
			- lm * bg + jg * md - ah * kn + ah * jo + kb * mh - jc * mh - pi * cf + of * di + pi * bg - ng * di - ob * hi + nc * hi;
}

/// Returns true if `pt' is in the tet (n1,n2,n3,n4).
bool pointInTet(vec3 pt, vec3 n1, vec3 n2, vec3 n3, vec3 n4)
{
	/*real d0 = mat4Det(n1.x(), n1.y(), n1.z(), 1, n2.x(), n2.y(), n2.z(), 1, n3.x(), n3.y(), n3.z(), 1, n4.x(), n4.y(), n4.z(), 1);

	if(equalsEpsilon(d0,0.0))
		return false;

	bool isPos=d0>-dEPSILON;

	real d1 = mat4Det(pt.x(), pt.y(), pt.z(), 1, n2.x(), n2.y(), n2.z(), 1, n3.x(), n3.y(), n3.z(), 1, n4.x(), n4.y(), n4.z(), 1);

	if((isPos && d1<dEPSILON) || (!isPos && d1>-dEPSILON))
		return false;

	real d2 = mat4Det(n1.x(), n1.y(), n1.z(), 1, pt.x(), pt.y(), pt.z(), 1, n3.x(), n3.y(), n3.z(), 1, n4.x(), n4.y(), n4.z(), 1);

	if((isPos && d2<dEPSILON) || (!isPos && d2>-dEPSILON))
		return false;

	real d3 = mat4Det(n1.x(), n1.y(), n1.z(), 1, n2.x(), n2.y(), n2.z(), 1, pt.x(), pt.y(), pt.z(), 1, n4.x(), n4.y(), n4.z(), 1);

	if((isPos && d3<dEPSILON) || (!isPos && d3>-dEPSILON))
		return false;

	real d4 = mat4Det(n1.x(), n1.y(), n1.z(), 1, n2.x(), n2.y(), n2.z(), 1, n3.x(), n3.y(), n3.z(), 1, pt.x(), pt.y(), pt.z(), 1);

	return (isPos && d4>-dEPSILON) || (!isPos && d4<dEPSILON);*/
	vec3 xi=pointSearchLinTet(pt,n1,n2,n3,n4);
	return xi.isInUnitCube() && (xi.x()+xi.y()+xi.z())<=1.0; // TODO: confirm this is correct?
}

bool pointInHex(vec3 pt, vec3 n1, vec3 n2, vec3 n3, vec3 n4, vec3 n5, vec3 n6, vec3 n7, vec3 n8)
{
	return pointSearchLinHex(pt,n1,n2,n3,n4,n5,n6,n7,n8).isInUnitCube();
}

vec3 pointSearchLinTet(vec3 pt, vec3 n1, vec3 n2, vec3 n3, vec3 n4)
{
	vec3 minv=n1; minv.setMinVals(n2); minv.setMinVals(n3); minv.setMinVals(n4);
	vec3 maxv=n1; maxv.setMaxVals(n2); maxv.setMaxVals(n3); maxv.setMaxVals(n4);

	if(!pt.inAABB(minv,maxv))
		return vec3(-1);

	real x1 = n1.x(), y1 = n1.y(), z1 = n1.z();
	real dx = pt.x() - x1, dy = pt.y() - y1, dz = pt.z() - z1;

	real dx2 = n2.x() - x1, dy2 = n2.y() - y1, dz2 = n2.z() - z1;
	real dx3 = n3.x() - x1, dy3 = n3.y() - y1, dz3 = n3.z() - z1;
	real dx4 = n4.x() - x1, dy4 = n4.y() - y1, dz4 = n4.z() - z1;

	// calculate the inverse determinant for the matrix A (see header for explanation)
	real invdet = 1.0/(dx2 * (dz4 * dy3 - dz3 * dy4) - dy2 * (dz4 * dx3 - dz3 * dx4) + dz2 * (dy4 * dx3 - dy3 * dx4));

	// calculate the inverse of the matrix A, multiply by the matrix pt and then by the inverse determinant all in one step
	real xi1 = invdet * ((dx * (dz4 * dy3 - dz3 * dy4)) + (dy * (dz3 * dx4 - dz4 * dx3)) + (dz * (dy4 * dx3 - dy3 * dx4)));
	real xi2 = invdet * ((dx * (dz2 * dy4 - dz4 * dy2)) + (dy * (dz4 * dx2 - dz2 * dx4)) + (dz * (dy2 * dx4 - dy4 * dx2)));
	real xi3 = invdet * ((dx * (dz3 * dy2 - dz2 * dy3)) + (dy * (dz2 * dx3 - dz3 * dx2)) + (dz * (dy3 * dx2 - dy2 * dx3)));

	return vec3(xi1,xi2,xi3);
}

// xi values for dividing a hex into 5 tets
vec3 divtets[5][4]={
	{vec3(0.0, 0.0, 0.0),vec3(1.0, 0.0, 1.0),vec3(1.0, 1.0, 0.0),vec3(0.0, 1.0, 1.0)},
	{vec3(0.0, 0.0, 0.0),vec3(1.0, 1.0, 0.0),vec3(0.0, 1.0, 0.0),vec3(0.0, 1.0, 1.0)},
	{vec3(0.0, 0.0, 0.0),vec3(1.0, 0.0, 1.0),vec3(0.0, 1.0, 1.0),vec3(0.0, 0.0, 1.0)},
	{vec3(1.0, 0.0, 1.0),vec3(1.0, 1.0, 0.0),vec3(0.0, 1.0, 1.0),vec3(1.0, 1.0, 1.0)},
	{vec3(0.0, 0.0, 0.0),vec3(1.0, 0.0, 0.0),vec3(1.0, 1.0, 0.0),vec3(1.0, 0.0, 1.0)}
};

vec3 pointSearchLinHex(vec3 pt, vec3 n1, vec3 n2, vec3 n3, vec3 n4, vec3 n5, vec3 n6, vec3 n7, vec3 n8)
{
	vec3 minv=n1,maxv=n1;
	minv.setMinVals(n2); minv.setMinVals(n3); minv.setMinVals(n4);
	minv.setMinVals(n5); minv.setMinVals(n6); minv.setMinVals(n7); minv.setMinVals(n8);
	maxv.setMaxVals(n2); maxv.setMaxVals(n3); maxv.setMaxVals(n4);
	maxv.setMaxVals(n5); maxv.setMaxVals(n6); maxv.setMaxVals(n7); maxv.setMaxVals(n8);

	if(!pt.inAABB(minv,maxv))
		return vec3(-1);

 	real coeffs[8];
 	vec3 tet[4];

 	// search each of the 5 tets for the point
 	for(int t=0;t<5;t++){
 		// calculate the tet's vertices by interpolating within the given hex
 		for(int n=0;n<4;n++){
 			vec3 tt=divtets[t][n];
 			basis_Hex1NL(tt.x(),tt.y(),tt.z(),coeffs);
 			tet[n]=n1*coeffs[0]+n2*coeffs[1]+n3*coeffs[2]+n4*coeffs[3]+n5*coeffs[4]+n6*coeffs[5]+n7*coeffs[6]+n8*coeffs[7];
 		}

 		vec3 xi=pointSearchLinTet(pt,tet[0],tet[1],tet[2],tet[3]);

 		// if the xi value is in simplex xi space then we're in the tet so interpolate using the hex xi coords (which define the tet) as the values
 		if(xi.isInUnitCube() && (xi.x()+xi.y()+xi.z())<=(1.0+dEPSILON)){
 			basis_Tet1NL(xi.x(),xi.y(),xi.z(),coeffs);
 			return divtets[t][0]*coeffs[0]+divtets[t][1]*coeffs[1]+divtets[t][2]*coeffs[2]+divtets[t][3]*coeffs[3];
 		}
 	}

	return vec3(-1);
}

realtriple calculateTriPlaneSlice(const vec3& planept, const vec3& planenorm, const vec3& a, const vec3& b, const vec3& c)
{
	if(a==b || b==c || a==c) // if the triangle is degenerate, return a negative result (0,0,0)
		return realtriple();

	real adist=a.planeDist(planept,planenorm);
	real bdist=b.planeDist(planept,planenorm);
	real cdist=c.planeDist(planept,planenorm);

	// if the distances are all the same or all points are on the same side of the plane, return a negative result
	if((adist==bdist && bdist==cdist) || (adist>=0 && bdist>=0 && cdist>=0) || (adist<=0 && bdist<=0 && cdist<=0))
		return realtriple();

	realtriple result;
	real adistsum=fabs(adist)+fabs(bdist);
	real bdistsum=fabs(bdist)+fabs(cdist);
	real cdistsum=fabs(adist)+fabs(cdist);

	if(adistsum>0)
		result.first=adist/adistsum;

	if(bdistsum>0)
		result.second=bdist/bdistsum;

	if(cdistsum>0)
		result.third=cdist/cdistsum;

	return result;
}

real calculateLinePlaneSlice(const vec3& planept, const vec3& planenorm, const vec3& a, const vec3& b)
{
	if(a==b)
		return 0;

	real adist=a.planeDist(planept,planenorm);
	real bdist=b.planeDist(planept,planenorm);

	// if the distances are all the same or all points are on the same side of the plane, return a negative result
	if(adist==bdist || (adist>=0 && bdist>=0) || (adist<=0 && bdist<=0))
		return 0;

	real distsum=fabs(adist)+fabs(bdist);
	if(distsum>0)
		return adist/distsum;

	return 0;
}

real calculateTetEdgeIntersect(real val, real a, real b)
{
	if(a<=val && val<=b)
		return lerpXi(val,a,b);

	if(b<=val && val<=a)
		return 1.0-lerpXi(val,b,a);

	return -1;
}

void calculateTetValueIntersects(real val, real a, real b, real c, real d, real* results)
{
	results[0]=calculateTetEdgeIntersect(val,a,b);
	results[1]=calculateTetEdgeIntersect(val,a,c);
	results[2]=calculateTetEdgeIntersect(val,a,d);
	results[3]=calculateTetEdgeIntersect(val,b,c);
	results[4]=calculateTetEdgeIntersect(val,b,d);
	results[5]=calculateTetEdgeIntersect(val,c,d);
}

sval calculateHexValueIntersects(real val,const real* vals,intersect* results)
{
	// indices of edges between vertices of hexahedron
	static sval indices[][2]={ {0,1}, {1,3}, {3,2}, {2,0}, {4,5}, {5,7}, {7,6}, {6,4}, {0,4}, {1,5}, {2,6}, {3,7} };

	sval count=0;
	real absvals[8];

	for(int i=0;i<8;i++) // pre-cache absolute differences between val and the value of each vertex
		absvals[i]=fabs(val-vals[i]);

	for(int i=0;i<12 && count<6;i++){ // check each edge for intersection, there are 12 edges and no more than 6 possible intersections
		sval i1=indices[i][0], i2=indices[i][1];
		real h1=vals[i1], h2=vals[i2];

		if(h1>=val ? h2<val : h2>=val){ // if h1 is greater than or equal to val and h2 is less, or vice versa, the edge is intersected
			real vsum=absvals[i1]+absvals[i2];
			results[count]=intersect(i1,i2,vsum==0 ? 0 : (absvals[i1]/vsum));
			count++;
		}
	}

	return count;
}

void interpolateImageStack(const std::vector<RealMatrix*>& stack,const transform& stacktransinv,RealMatrix *out,const transform& outtrans)
{
	sval n=out->n()-1,m=out->m()-1;

	out->fill(0);

	real minval=stack[0]->at(0,0);
	real maxval=minval;

	mat4 trans=stacktransinv.toMatrix()*outtrans.toMatrix();

	for(sval i=0;i<=n;i++){
		for(sval j=0;j<=m;j++){
			vec3 xi=vec3(real(j)/m,real(i)/n); // the xi value of the position (i,j) in `out'
			vec3 pos=xi*trans;

			if(pos.isInUnitCube(dEPSILON)){
				real val=getImageStackValue(stack,pos.clamp(vec3(0),vec3(1)));
				out->at(i,j)=val;
				minval=_min(val,minval);
				maxval=_max(val,maxval);
			}
		}
	}

	setMatrixMinMax<real,real>(out,minval,maxval);
}


real getImageStackValue(const std::vector<RealMatrix*>& stack,const vec3& pos)
{
	vec3 cpos=pos.clamp(vec3(dEPSILON),vec3(1-dEPSILON));
	real numimgs1=real(stack.size())-1;
	sval img1=sval(floor(cpos.z()*numimgs1));
	sval img2=sval(ceil(cpos.z()*numimgs1));
	real dz=numimgs1==0 ? 0 :lerpXi(cpos.z(),img1/numimgs1,img2/numimgs1);

	return trilerpMatrices(stack[img1],stack[img2],vec3(cpos.x(),cpos.y(),dz),vec3(cpos.x(),cpos.y(),1.0-dz));
}


void calculateImageHistogram(const RealMatrix* img, RealMatrix* hist,i32 minv)
{
	sval n=img->n(), m=img->m(), hn=hist->n();

	for(sval i=0;i<n;i++)
		for(sval j=0;j<m;j++){
			sval val=sval(i32(img->at(i,j)+0.5)-minv);
			if(val<hn)
				hist->at(val)++;
		}
}

} // namespace RenderTypes

