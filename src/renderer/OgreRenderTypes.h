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

#ifndef RENDERSCENE_H_
#define RENDERSCENE_H_

#include <Ogre.h>
#include <OgrePlugin.h>
#include <OgreOverlaySystem.h>
#include <OgreFontManager.h>

#include "RenderTypes.h"

#define TOSTR(v) Ogre::StringConverter::toString(v)

#define THROW_RENDEREX(e) throw RenderException(e.getFullDescription().c_str(),__FILE__,__LINE__)

#define MAXNAMECOUNT 1000000 // maximum number to append to names when creating unique names

namespace OgreRenderTypes
{

using namespace RenderTypes;

typedef std::pair<vec3,vec3> planevert;

class OgreRenderScene;

/// Set `node' to have the same parent node as that of `fig'.
void setNodeFigParent(Ogre::SceneNode* node,Figure *fig,OgreRenderScene* scene);

/// Set the visibility of `obj' to be `isVisible' for the camera `cam'. If `cam' is NULL then `obj' becomes visible/invisible to all cameras.
void setCameraVisibility(const Camera* cam,Ogre::MovableObject* obj, bool isVisible,OgreRenderScene* scene);

/// Deletes the `node' and `obj' objects in a thread-safe manner at some future time (probably next render cycle).
void destroySceneNode(Ogre::SceneNode *node,Ogre::MovableObject* obj,OgreRenderScene *scene);

inline Ogre::ColourValue convert(const color & c)
{
	return Ogre::ColourValue(c.r(), c.g(), c.b(), c.a());
}

inline color convert(const Ogre::ColourValue & c)
{
	return color(c.r, c.g, c.b, c.a);
}

inline Ogre::Vector3 convert(const vec3 & v)
{
	return Ogre::Vector3((float)v.x(),(float)v.y(),(float)v.z());
}

inline vec3 convert(const Ogre::Vector3 & v)
{
	return vec3(v.x,v.y,v.z);
}

inline Ogre::Quaternion convert(const rotator & r)
{
	return Ogre::Quaternion((float)r.w(),(float)r.x(),(float)r.y(),(float)r.z());
}

inline rotator convert(const Ogre::Quaternion & r)
{
	rotator rr;
	rr.set(r.x,r.y,r.z,r.w);
	return rr;
}

inline Ogre::GpuProgramType convert(ProgramType pt)
{
	switch(pt){
	case PT_FRAGMENT : return Ogre::GPT_FRAGMENT_PROGRAM;
	case PT_GEOMETRY : return Ogre::GPT_GEOMETRY_PROGRAM;
	case PT_VERTEX   : 
	default          : return Ogre::GPT_VERTEX_PROGRAM;
	}
}

inline Ogre::PixelFormat convert(TextureFormat format)
{
	switch(format){
	case TF_RGBA32    : return Ogre::PF_R8G8B8A8;
	case TF_ARGB32    : return Ogre::PF_A8R8G8B8;
	case TF_RGB24     : return Ogre::PF_R8G8B8;
	case TF_ALPHA8    : return Ogre::PF_A8;
	case TF_LUM8      : return Ogre::PF_L8;
	case TF_LUM16     : return Ogre::PF_L16;
	case TF_ALPHALUM8 : return Ogre::PF_A4L4;
	default           : return Ogre::PF_UNKNOWN;
	}
}

inline TextureFormat convert(Ogre::PixelFormat format)
{
	switch(format){
	case Ogre::PF_R8G8B8A8 : return TF_RGBA32;
	case Ogre::PF_A8R8G8B8 : return TF_ARGB32;
	case Ogre::PF_R8G8B8   : return TF_RGB24;
	case Ogre::PF_A8       : return TF_ALPHA8;
	case Ogre::PF_L8       : return TF_LUM8;
	case Ogre::PF_L16      : return TF_LUM16;
	case Ogre::PF_A4L4     : return TF_ALPHALUM8;
	default                : return TF_UNKNOWN;
	}
}

inline Ogre::RenderOperation::OperationType convert(FigureType type)
{	
	switch(type){
	case FT_POINTLIST : return Ogre::RenderOperation::OT_POINT_LIST;
	case FT_LINELIST  : return Ogre::RenderOperation::OT_LINE_LIST; 
	case FT_TRISTRIP  : return Ogre::RenderOperation::OT_TRIANGLE_STRIP;
	case FT_TRILIST   :   
	default           : return Ogre::RenderOperation::OT_TRIANGLE_LIST;
	}
}

/**
 * Base class used by specializations with the renderer to destroy and update resources within the render cycle. The name
 * of the creating object should be passed in the constructor for operations which might be performed after an object has
 * been deleted. Objects who may have operations pending when their destructors are called can remove them from the queue
 * using the OgreRenderScene::removeResourceOp() method in their destructors with their own names as the argument; this
 * will ensure any operation with that name as its `parentname' field will be removed before being called.
 */
class ResourceOp
{
public:
	/// Name of parent object which created this op and whose internal state is associated with it  
	std::string parentname; 
	ResourceOp(std::string parentname="") : parentname(parentname) {}
	/// Before each render operation, this method is called for every ResourceOp object the renderer stores, the object is deleted
	virtual void op() {}
};

/// The op() method calls the method commit() with the given object `obj' as the receiver.
template<typename T>
class CommitOp : public ResourceOp
{
public:
	T* obj;
	CommitOp(T* obj) : ResourceOp(obj->getName()), obj(obj){}
	virtual void op() { obj->commit(); }
};

/// Given a resource manager type M, calls remove() with the given name on the singleton instance of M.
template<typename M>
class RemoveResourceOp : public ResourceOp
{
public:
	std::string name;
	RemoveResourceOp(const std::string &name) : name(name) {}
	virtual void op(){ M::getSingleton().remove(name); }
};

/// Destroys the given object/node pair by detaching the node and detroying it, then deleting the object.
class DestroySceneNodeOp : public ResourceOp
{
public:
	Ogre::MovableObject* obj;
	Ogre::SceneNode *node;
	OgreRenderScene *scene;
	DestroySceneNodeOp(Ogre::MovableObject* obj,Ogre::SceneNode *node,OgreRenderScene *scene) : obj(obj), node(node),scene(scene) {}
	virtual void op();
};

class DLLEXPORT OgreImage : public Image
{
	Ogre::Image img;
public:
	OgreImage(const Ogre::Image& i) :img(i) {}
	virtual ~OgreImage() {} 

	virtual TextureFormat getFormat() const { return convert(img.getFormat()); }
	virtual sval getWidth() const { return sval(img.getWidth()); }
	virtual sval getHeight() const { return sval(img.getHeight()); }
	virtual sval getDepth() const { return sval(img.getDepth()); }

	virtual size_t getDataSize() const { return img.getSize(); }
	virtual u8* getData() { return (u8*)img.getData(); }
	virtual std::string encode(const std::string& format) 
	{ 
		Ogre::DataStreamPtr p= img.encode(format); 
		return p->getAsString();
	}

	virtual void fillRealMatrix(RealMatrix* mat) throw(IndexException)
	{
		if(getWidth()!=mat->m())
			throw IndexException("Matrix has incorrect number of columns",mat->m(),getWidth());

		if(getHeight()!=mat->n())
			throw IndexException("Matrix has incorrect number of rows",mat->n(),getHeight());

		const char* data=(const char*)getData();

		switch(getFormat()){
		case TF_ALPHA8: 
		case TF_LUM8: convertUByteStreamToRealMatrix(data,mat);break;
		case TF_LUM16: convertUShortStreamToRealMatrix(data,mat);break;

		// not used?
		//case TF_RGBA32: convertRGBA32StreamToRealMatrix(data,mat); break;
		//case TF_RGB24: 
		//case TF_ALPHALUM8: break;

		default:
			Ogre::PixelBox pb=img.getPixelBox();
			sval w=_min<sval>(getWidth(),mat->m());
			sval h=_min<sval>(getHeight(),mat->n());

			for(sval y=0;y<h;y++)
				for(sval x=0;x<w;x++){
					Ogre::ColourValue cv=pb.getColourAt(x,y,0);
					mat->setAt((cv.r+cv.g+cv.b)/3.0,y,x);
				}

		}
	}

	virtual void fillColorMatrix(ColorMatrix* mat) throw(IndexException)
	{
	}
};

class DLLEXPORT OgreCamera: public Camera
{
protected:
	Ogre::Camera *camera;
	Ogre::Viewport *port;
	OgreRenderScene *scene;
	u32 id;

	Ogre::TexturePtr rtt_texture;

	vec3 position,lookat;
public:
	OgreCamera(Ogre::Camera * camera, Ogre::Viewport *port, OgreRenderScene * scene,u32 id) :
			camera(camera), port(port), scene(scene),id(id)
	{
		rtt_texture.setNull();
	}

	virtual ~OgreCamera();

	virtual const char* getName() const
	{
		return camera->getName().c_str();
	}

	virtual vec3 getPosition() const { return position;}
	virtual vec3 getLookAt() const { return lookat;}

	virtual rotator getRotation() const { return convert(camera->getDerivedOrientation()); }

	virtual vec3 getScreenPosition(vec3 pos) const 
	{
		Ogre::Vector4 p = camera->getProjectionMatrix() * camera->getViewMatrix() * Ogre::Vector4(pos.x(),pos.y(),pos.z(),1);
		real w=port->getActualWidth(),h=port->getActualHeight();

		return vec3(fround(w*(0.5+0.5*(p.x/p.w))),fround(h*(0.5-0.5*(p.y/p.w))));
	}

	virtual void setPosition(const vec3& v)
	{
		camera->setPosition(v.x(), v.y(), v.z());
		position=v;
	}

	virtual void setLookAt(const vec3 & v)
	{
		camera->lookAt(v.x(), v.y(), v.z());
		lookat=v;
	}

	virtual void rotate(const rotator & r)
	{
		camera->rotate(convert(r));
	}

	virtual void setRotation(const rotator& r) 
	{ 
		camera->setOrientation(convert(r)); 
	}

	virtual void setUp(const vec3 & v)
	{
	}

	virtual void setZUp()
	{
		// http://www.ogre3d.org/forums/viewtopic.php?f=2&t=62410

		Ogre::Vector3 look=convert(lookat);
		Ogre::Vector3 pos=convert(position);

		Ogre::Vector3 v1 = look - pos;
		Ogre::Vector3 v2 = v1.crossProduct(Ogre::Vector3::UNIT_Z);
		Ogre::Vector3 v3 = v2.crossProduct(v1);
		Ogre::Quaternion rot = camera->getOrientation().yAxis().getRotationTo(v3);
		camera->rotate(rot);
	}

	virtual void setNearClip(real dist)
	{
		camera->setNearClipDistance(_max<real>(0.0000001,dist));
	}

	virtual void setFarClip(real dist)
	{
		camera->setFarClipDistance(_max<real>(0.0000001,dist));
	}

	virtual void setVertFOV(real rads)
	{
		camera->setFOVy(Ogre::Radian(_max<real>(0.00001,rads)));
	}

	virtual real getVertFOV() const 
	{
		return camera->getFOVy().valueRadians();
	}
	
	virtual real getNearClip() const 
	{
		return camera->getNearClipDistance();	
	}
	
	virtual real getFarClip() const 
	{
		return camera->getFarClipDistance(); 
	}

	virtual sval getWidth() const 
	{ 
		return port->getActualWidth(); 
	}

	virtual sval getHeight() const
	{
		return port->getActualHeight();
	}
	
	virtual u32 getVisibilityMask() const
	{
		return port->getVisibilityMask();
	}

	virtual void setBGColor(const color & c)
	{
		port->setBackgroundColour(convert(c));
		port->setClearEveryFrame(true,c.a()==1.0f ? Ogre::FBT_COLOUR|Ogre::FBT_DEPTH : Ogre::FBT_DEPTH);
	}

	virtual void setAspectRatio(real rat)
	{
		camera->setAspectRatio(rat);
	}

	virtual real getAspectRatio() const
	{ 
		return camera->getAspectRatio();
	}
	
	virtual Ray* getProjectedRay(real x, real y, bool isAbsolute=true) const
	{
		if(isAbsolute){
			real w=port->getActualWidth(),h=port->getActualHeight();

			if(w>0 && h>0){
				x/=w;
				y/=h;
			}
		}
		
		Ogre::Ray r=camera->getCameraToViewportRay(x,y);
		
		return new Ray(convert(r.getPoint(0.0)),convert(r.getDirection()));
	}

	virtual void setViewport(real left=0.0f,real top=0.0f,real width=1.0f,real height=1.0f)
	{
		port->setDimensions(left,top,width,height);
		if(camera->getProjectionType()==Ogre::PT_ORTHOGRAPHIC)
			camera->setOrthoWindow((width-left)*port->getActualWidth(),(height-top)*port->getActualHeight());
	}

	virtual void setOrtho(bool isOrtho)
	{
		camera->setProjectionType(isOrtho ? Ogre::PT_ORTHOGRAPHIC : Ogre::PT_PERSPECTIVE);
	}
	
	virtual void setWireframe(bool isWireframe)
	{
		camera->setPolygonMode(isWireframe ? Ogre::PM_WIREFRAME : Ogre::PM_SOLID);
	}

	virtual void setSecondaryCamera(bool secondary)
	{
		// primary cameras have 1 as their flag, secondaries have a bit corresponding to ID number
		port->setVisibilityMask(secondary ? u32(1)<<(id+1) : 1);
		port->setSkiesEnabled(!secondary); // doesn't work?
	}

	virtual bool isPointInViewport(int x, int y) const 
	{
		x-=port->getActualLeft();
		y-=port->getActualTop();
		return x>=0 && x<=port->getActualWidth() && y>=0 && y<=port->getActualHeight(); 
	} 
	
	virtual bool isSecondaryCamera() { return port->getVisibilityMask()!=1; }

	virtual void renderToFile(const std::string& filename,sval width,sval height, TextureFormat format=TF_RGB24,real stereoOffset=0.0) throw(RenderException)
	{
		renderToTexture(width,height,format,stereoOffset);
		rtt_texture->getBuffer()->getRenderTarget()->writeContentsToFile(filename);
	}

	virtual void renderToStream(void* stream,sval width,sval height, TextureFormat format=TF_RGB24,real stereoOffset=0.0) throw(RenderException) 
	{
		renderToTexture(width,height,format,stereoOffset);
		Ogre::PixelBox pb(width,height,1,convert(format),stream);
		rtt_texture->getBuffer()->blitToMemory(pb);
	}
	
	virtual Image* renderToImage(sval width,sval height, TextureFormat format=TF_RGB24,real stereoOffset=0.0) throw(RenderException)
	{
		Ogre::Image img;
		Ogre::PixelFormat pf=convert(format);
		Ogre::uchar* buf=OGRE_ALLOC_T(Ogre::uchar, Ogre::PixelUtil::getMemorySize(width,height,1,pf), Ogre::MEMCATEGORY_GENERAL);
		
		img.loadDynamicImage(buf,width,height,1,pf);
		renderToStream((u8*)buf,width,height,format,stereoOffset);
		
		return new OgreImage(img);
	}

protected:
	/// Render to the off-screen texture `rtt_texture' with the given parameters in stereo if `stereoOffset'>0.0
	void renderToTexture(sval width,sval height,TextureFormat format,real stereoOffset) throw(RenderException);
};

class DLLEXPORT OgreMaterial : public Material
{
	static const sval SPECWIDTH=100;

protected:
	/// The root scene which renders this object
	OgreRenderScene *scene;
	
	Ogre::MaterialPtr mat;
	Ogre::Pass* t0p0;
	Ogre::TextureUnitState* texunit;
	BlendMode bm;
	bool _useTexFiltering;
	bool _isClampTexAddress;

	std::string fragname;
	std::string geomname;
	std::string vertname;

	Ogre::TexturePtr spectex;
	Ogre::TextureUnitState* specunit;
	
public:
	OgreMaterial(Ogre::MaterialPtr mat,OgreRenderScene *scene) : mat(mat), scene(scene), bm(BM_ALPHA),
		t0p0(mat->getTechnique(0)->getPass(0)),texunit(0),_useTexFiltering(true),
		_isClampTexAddress(false),specunit(0)
	{
		mat->setLightingEnabled(true);
		
		t0p0->setDepthWriteEnabled(true); // use depth function in depth buffer
		t0p0->setDepthCheckEnabled(true); // enable depth buffer checking
		t0p0->setSceneBlending(Ogre::SBT_TRANSPARENT_ALPHA); // use alpha channel when blending pixels into depth buffer
		t0p0->setAlphaRejectSettings(Ogre::CMPF_GREATER,2); // only draw pixels with an alpha channel value greater than this
		t0p0->setTransparentSortingEnabled(true);
		t0p0->setTransparentSortingForced(true);
		t0p0->setVertexColourTracking(Ogre::TVC_AMBIENT|Ogre::TVC_DIFFUSE);
		t0p0->setPointSize(2.0);
	}
	
	virtual ~OgreMaterial();
	
	/// Cloning must be done in the main thread
	virtual Material* clone(const char* name) const;
	
	virtual void copyTo(Material* m,bool copyTex=false,bool copySpec=false,bool copyProgs=false) const 
	{
		m->setAmbient(getAmbient());
		m->setDiffuse(getDiffuse());
		m->setSpecular(getSpecular());
		m->setEmissive(getEmissive());

		m->setShininess(getShininess());
		m->setPointSize(getPointSizeMin(),getPointSizeMax());
		m->setPointSizeAbs(getPointSizeAbs());
		m->setPointAttenuation(usesPointAttenuation());

		m->useVertexColor(usesVertexColor());
		m->useDepthCheck(usesDepthCheck());
		m->useDepthWrite(usesDepthWrite());
		m->useTexFiltering(usesTexFiltering());
		m->clampTexAddress(isClampTexAddress());
		m->useFlatShading(usesFlatShading());
		m->useLighting(usesLighting());
		m->cullBackfaces(isCullBackfaces());
		m->usePointSprites(usesPointSprites());

		m->setAlpha(getAlpha());
		m->useInternalAlpha(usesInternalAlpha());
		m->setBlendMode(bm);

		m->setLinearAlpha(isLinearAlpha());
		
		if(copyTex)
			m->setTexture(getTexture());
		
		if(copySpec)
			m->copySpectrumFrom(this);
		
		if(copyProgs){
			m->setGPUProgram(getGPUProgram(PT_VERTEX),PT_VERTEX);
			m->setGPUProgram(getGPUProgram(PT_FRAGMENT),PT_FRAGMENT);
			m->setGPUProgram(getGPUProgram(PT_GEOMETRY),PT_GEOMETRY);
		}
	}

	virtual const char* getName() const { return mat->getName().c_str(); }

	virtual color getAmbient() const { return convert(t0p0->getAmbient()); }
	virtual color getDiffuse() const { return convert(t0p0->getDiffuse()); }
	virtual color getSpecular() const { return convert(t0p0->getSpecular()); }
	virtual color getEmissive() const { return convert(t0p0->getSelfIllumination()); }
	
	virtual real getShininess() const { return t0p0->getShininess(); }
	virtual real getPointSizeMin() const { return t0p0->getPointMinSize(); }
	virtual real getPointSizeMax() const { return t0p0->getPointMaxSize(); }
	virtual real getPointSizeAbs() const { return t0p0->getPointSize(); }
	
	virtual bool usesPointAttenuation() const { return t0p0->isPointAttenuationEnabled(); }
	
	virtual BlendMode getBlendMode() const { return bm; }
	
	virtual bool usesVertexColor() const {return t0p0->getVertexColourTracking() !=Ogre::TVC_NONE; }
	virtual bool usesLighting() const { return t0p0->getLightingEnabled(); }
	virtual bool usesFlatShading() const { return t0p0->getShadingMode() == Ogre::SO_FLAT; }
	virtual bool usesDepthCheck() const { return t0p0->getDepthCheckEnabled(); }
	virtual bool usesDepthWrite() const { return t0p0->getDepthWriteEnabled(); }
	virtual bool usesTexFiltering() const { return _useTexFiltering; }
	virtual bool isCullBackfaces() const { return t0p0->getCullingMode()!=Ogre::CULL_NONE; }
	virtual bool usesPointSprites() const { return t0p0->getPointSpritesEnabled(); }
	virtual const char* getTexture() const { return texunit!=NULL ? texunit->getTextureName().c_str() : ""; }
	
	virtual const char* getGPUProgram(ProgramType pt) const
	{
		switch(pt){
		case PT_FRAGMENT : return fragname.c_str();
		case PT_GEOMETRY : return geomname.c_str();
		default:
		case PT_VERTEX   : return vertname.c_str();
		}
	}

	virtual void setAmbient(const color & c) { mat->setAmbient(c.r(),c.g(),c.b()); }
	virtual void setDiffuse(const color & c) { mat->setDiffuse(c.r(),c.g(),c.b(),useAlpha ? alpha : c.a()); }
	virtual void setSpecular(const color & c) { mat->setSpecular(c.r(),c.g(),c.b(),useAlpha ? alpha : c.a()); }
	virtual void setEmissive(const color & c) { mat->setSelfIllumination(c.r(),c.g(),c.b()); }
	virtual void setShininess(real c) { mat->setShininess(c); }

	virtual void setPointSize(real min,real max)
	{
		t0p0->setPointMinSize(min);
		t0p0->setPointMaxSize(max);
	}

	virtual void setPointSizeAbs(real size)
	{
		t0p0->setPointSize(size);
	}

	virtual void setPointAttenuation(bool enabled,real constant=0.0f,real linear=1.0f, real quad=0.0f)
	{
		t0p0->setPointAttenuation(enabled,constant,linear,quad);
	}
	
	virtual void setBlendMode(BlendMode bm)
	{
		this->bm=bm;
		Ogre::SceneBlendType sbt=Ogre::SBT_TRANSPARENT_ALPHA;
		
		switch(bm){
		case BM_ALPHA:   
			sbt=Ogre::SBT_TRANSPARENT_ALPHA;
			break;
		case BM_COLOR:   
			sbt=Ogre::SBT_TRANSPARENT_COLOUR;
			break;
		case BM_ADD:     
			sbt=Ogre::SBT_ADD;
			break; 	
		case BM_MOD:     
			sbt=Ogre::SBT_MODULATE;
			break; 	
		case BM_REPLACE: 
			sbt=Ogre::SBT_REPLACE;
			break;
		}
		
		t0p0->setSceneBlending(sbt);
	}

	virtual void usePointSprites(bool useSprites)
	{
		t0p0->setPointSpritesEnabled(useSprites);
	}

	virtual void useVertexColor(bool use)
	{
		t0p0->setVertexColourTracking(use ? (Ogre::TVC_AMBIENT|Ogre::TVC_DIFFUSE) : Ogre::TVC_NONE);
	}

	virtual void useLighting(bool use)
	{
		t0p0->setLightingEnabled(use);
	}
	
	virtual void useFlatShading(bool use) 
	{
		t0p0->setShadingMode(use ? Ogre::SO_FLAT : Ogre::SO_GOURAUD);
	}
	
	virtual void useDepthCheck(bool use) { t0p0->setDepthCheckEnabled(use); }
	virtual void useDepthWrite(bool use) { t0p0->setDepthWriteEnabled(use); }

	virtual void useTexFiltering(bool use) 
	{ 
		_useTexFiltering=use;
		if(texunit!=NULL)
			texunit->setTextureFiltering(use ? Ogre::TFO_BILINEAR :Ogre::TFO_NONE); 
	}

	virtual void clampTexAddress(bool use)
	{
		_isClampTexAddress=use;
		if(texunit!=NULL)
			texunit->setTextureAddressingMode(use ? Ogre::TextureUnitState::TAM_CLAMP : Ogre::TextureUnitState::TAM_WRAP);
	}

	virtual void cullBackfaces(bool cull)
	{
		mat->setCullingMode(cull ? Ogre::CULL_CLOCKWISE : Ogre::CULL_NONE);
	}

	virtual void setTexture(const char* name);

	virtual void useSpectrumTexture(bool use);

	virtual void updateSpectrum();
	
	/// commits the spectrum colors to the spectrum texture if used, called indirectly by updateSpectrum()
	void commit();
	
	virtual void setGPUProgram(const std::string& name, ProgramType pt) 
	{
		Ogre::HighLevelGpuProgramPtr chosenprog=getGPUProgByNumberedName(name);
		std::string chosenname=(chosenprog.isNull() || chosenprog->hasCompileError())? "" : chosenprog->getName();

		if(chosenname.size()==0 && strlen(getGPUProgram(pt))==0)
			return;

		switch(pt){
		case PT_FRAGMENT: 
			fragname=name;
			t0p0->setFragmentProgram(chosenname); 
			break;
		case PT_GEOMETRY: 
			geomname=name;
			t0p0->setGeometryProgram(chosenname); 
			break;
		case PT_VERTEX: 
			vertname=name;
			t0p0->setVertexProgram(chosenname); 
			break;
		}                 
	}

	virtual bool setGPUParamInt(ProgramType pt,const std::string& name, int val) 
	{ 
		Ogre::GpuProgramParametersSharedPtr params=getGPUParameters(pt);

		if(!params.isNull() && params->_findNamedConstantDefinition(name)!=NULL){
			params->setNamedConstant(name,val);
			return true;
		}

		return false; 
	}

	virtual bool setGPUParamReal(ProgramType pt,const std::string& name, real val) 
	{ 
		Ogre::GpuProgramParametersSharedPtr params=getGPUParameters(pt);

		if(!params.isNull() && params->_findNamedConstantDefinition(name)!=NULL){
			params->setNamedConstant(name,float(val));
			return true;
		}

		return false; 
	}

	virtual bool setGPUParamVec3(ProgramType pt,const std::string& name, vec3 val)
	{ 
		Ogre::GpuProgramParametersSharedPtr params=getGPUParameters(pt);

		if(!params.isNull() && params->_findNamedConstantDefinition(name)!=NULL){
			params->setNamedConstant(name,convert(val));
			return true;
		}

		return false; 
	}

	virtual bool setGPUParamColor(ProgramType pt,const std::string& name, color val) 
	{ 
		Ogre::GpuProgramParametersSharedPtr params=getGPUParameters(pt);

		if(!params.isNull() && params->_findNamedConstantDefinition(name)!=NULL){
			params->setNamedConstant(name,convert(val));
			return true;
		}

		return false; 
	}

private:
	Ogre::HighLevelGpuProgramPtr getGPUProgByNumberedName(const std::string& name)
	{
		Ogre::HighLevelGpuProgramPtr result;
		std::string chosenname="";

		if(name.size()>0){
			std::string namebar=name+"|";

			Ogre::HighLevelGpuProgramManager::ResourceMapIterator i=Ogre::HighLevelGpuProgramManager::getSingleton().getResourceIterator();
			
			while(i.hasMoreElements()){
				Ogre::ResourcePtr p=i.getNext();
				Ogre::HighLevelGpuProgramPtr prog=Ogre::HighLevelGpuProgramManager::getSingleton().getByName(p->getName());  //i.getNext();
				std::string pname=prog->getName();

				if(pname.substr(0,namebar.size())==namebar && (pname.size()>chosenname.size() || pname.compare(name)>0)){
					chosenname=pname;
					result=prog;
				}
			}
		}

		return result;
	}

	Ogre::GpuProgramParametersSharedPtr getGPUParameters(ProgramType pt)
	{
		Ogre::GpuProgramParametersSharedPtr params;
		std::string name(getGPUProgram(pt));

		if(name.size()>0){
			switch(pt){
			case PT_FRAGMENT: params=t0p0->getFragmentProgramParameters(); break;
			case PT_GEOMETRY: params=t0p0->getGeometryProgramParameters(); break;
			case PT_VERTEX:   params=t0p0->getVertexProgramParameters(); break;
			}

			if(params.isNull()){
				Ogre::HighLevelGpuProgramPtr chosenprog=getGPUProgByNumberedName(name);

				if(!chosenprog.isNull() && !chosenprog->hasCompileError()){
					params=chosenprog->createParameters();

					switch(pt){
					case PT_FRAGMENT: t0p0->setFragmentProgramParameters(params); break;
					case PT_GEOMETRY: t0p0->setGeometryProgramParameters(params); break;
					case PT_VERTEX:   t0p0->setVertexProgramParameters(params); break;
					}
				}
			}
		}

		return params;
	}
};

class DLLEXPORT OgreLight : public Light
{
protected:
	Ogre::Light* light;
	OgreRenderScene *scene;

public:
	OgreLight(Ogre::Light* light, OgreRenderScene *scene) : light(light), scene(scene)
	{}

	virtual ~OgreLight();

	virtual void setPosition(vec3 &v) { light->setPosition(convert(v)); }
	virtual void setDirection(vec3 &v) { light->setDirection(convert(v)); }
	virtual void setDiffuse(const color & c) { light->setDiffuseColour(convert(c)); }
	virtual void setSpecular(const color & c) { light->setSpecularColour(convert(c)); }

	virtual void setDirectional() { light->setType(Ogre::Light::LT_DIRECTIONAL); }
	virtual void setPoint() { light->setType(Ogre::Light::LT_POINT); }
	virtual void setSpotlight(real radsInner, real radsOuter, real falloff=1.0f)
	{
		light->setType(Ogre::Light::LT_SPOTLIGHT);
		light->setSpotlightRange(Ogre::Radian(radsInner),Ogre::Radian(radsOuter),falloff);
	}

	virtual void setAttenuation(real range, real constant=0.0f,real linear=1.0f, real quad=0.0f)
	{
		light->setAttenuation(range,constant,linear,quad);
	}

	virtual void setVisible(bool isVisible) { light->setVisible(isVisible); }
	
	virtual bool isVisible() const { return light->isVisible(); }
};


/** 
 * This is the base class for Ogre renderables used by the Figure subtypes.
 *
 * It manages Ogre vertex and index hardware data buffers directly and provides facilities for filling data into local 
 * buffers which are later copied to the hardware buffers. It extends the basic Ogre types needed to represent a 
 * renderable object in a scene. It uses an internal Vertex type having position, normal, color, and texture components.
 */
class OgreBaseRenderable : public Ogre::MovableObject, public Ogre::Renderable
{
public:
	/// Fixed definition of a vertex used in the renderer 
	struct Vertex
	{
		float pos[3];
		float norm[3];
		Ogre::RGBA col;
		float tex[3]; // 3D texture coordinates for volume textures
	};

protected:

	/// Parent figure this renderable is used by
	Figure *parent;
	/// The root scene which renders this object
	OgreRenderScene *scene;

	/// Sets vertex buffer to be write only
	static Ogre::HardwareBuffer::Usage vertexBufferUsage;
	/// Sets index buffer to be write only
	static Ogre::HardwareBuffer::Usage indexBufferUsage;
	
	Ogre::VertexData* vertexData;
	Ogre::HardwareVertexBufferSharedPtr vertBuf;
	
	Ogre::IndexData* indexData;
	
	Ogre::RenderOperation::OperationType _opType;

	bool deferFillOp;
	
	size_t _numVertices;
	size_t _numIndices;

	/// Vertex buffer in main memory used to stage data before being committed to video memory
	Vertex *localVertBuff;
	/// Index buffer in main memory used to stage data before being committed to video memory
	indexval *localIndBuff;
	
	Ogre::MaterialPtr mat;
	
	Ogre::AxisAlignedBox aabb;
	Ogre::Real boundRad;
	
	Ogre::String movableType;

	vec3 lastCamPos;
	bool depthSorting;

	Mutex mutex;

public:	
	OgreBaseRenderable(const std::string& name,const std::string& matname,Ogre::RenderOperation::OperationType opType,Ogre::SceneManager *mgr) throw(RenderException);
	
	virtual ~OgreBaseRenderable() { destroyBuffers(); deleteLocalVertBuff(); deleteLocalIndBuff(); }

	void setParentObjects(Figure *parent,OgreRenderScene *scene) { this->parent=parent; this->scene=scene; }

	void setDepthSorting(bool val) { depthSorting=val; }

	Mutex* getMutex()  { return &mutex; }
	
	/// Create the hardware buffers with the given number of vertices and indices (NOTE: must be executed in renderer thread)
	virtual void createBuffers(size_t numVerts,size_t numInds,bool deferCreate=false);
	
	/// Delete the hardware and local buffers (NOTE: must be executed in renderer thread)
	virtual void destroyBuffers();
	
	virtual void _updateRenderQueue(Ogre::RenderQueue* queue) ;
	virtual void getRenderOperation(Ogre::RenderOperation& op);
	virtual void _notifyCurrentCamera(Ogre::Camera* cam);

	/// Get (and allocate if needed) the local memory vertex buffer of the same size as the hardware buffer
	Vertex* getLocalVertBuff();
	
	/// Get (and allocate if needed) the local memory index buffer of the same size as the hardware buffer
	indexval* getLocalIndBuff();
	
	/// Copy the local buffers to the hardware buffers (NOTE: must be executed in renderer thread)
	void commitBuffers(bool commitVert=true, bool commitInd=true);
	/// Copy the data from matrices to the hardware buffers (NOTE: must be executed in renderer thread)
	void commitMatrices(const Matrix<Vertex>* verts,const IndexMatrix *inds);
	
	void deleteLocalVertBuff() { SAFE_DELETE(localVertBuff); }
	void deleteLocalIndBuff() { SAFE_DELETE(localIndBuff); }

	void fillDefaultData(bool deferFill=false);
	
	size_t numVertices() const { return _numVertices; }
	size_t numIndices() const { return _numIndices; }

	Ogre::RenderOperation::OperationType opType() const { return _opType; }
	
	Ogre::HardwareVertexBufferSharedPtr getVertexBuffer() const { return vertBuf; }
	Ogre::HardwareIndexBufferSharedPtr getIndexBuffer() const { return indexData->indexBuffer;}
	
	virtual const Ogre::MaterialPtr& getMaterial() const { return mat; }
	
	virtual void setMaterial(const Ogre::MaterialPtr& m) { mat=m; }
	virtual void setMaterial(const std::string &m) throw(RenderException)
	{ 
		try{
			Ogre::MaterialPtr mattemp=Ogre::MaterialManager::getSingleton().getByName(m);

			if(mattemp.isNull()){
				std::ostringstream out;
				out << "Cannot find material " << m;
				throw RenderException(out.str());
			}
			else
				mat=mattemp;
		} catch(Ogre::Exception &e){
			THROW_RENDEREX(e);
		}
	}
	
	virtual void getWorldTransforms(Ogre::Matrix4 *xform) const { *xform = _getParentNodeFullTransform(); }
	
	virtual Ogre::Real getSquaredViewDepth(const Ogre::Camera* cam) const { return mParentNode->getSquaredViewDepth(cam); }
	
	virtual const Ogre::LightList& getLights() const { return queryLights(); }
	
	virtual const Ogre::String& getMovableType() const { return movableType; }
	
	virtual const Ogre::AxisAlignedBox& getBoundingBox() const { return aabb; }
	
	virtual Ogre::Real getBoundingRadius() const { return boundRad; }

	virtual void setBoundingBox(vec3 minv, vec3 maxv) 
	{ 
		aabb.setExtents(convert(minv),convert(maxv)); 
		boundRad=Ogre::Math::boundingRadiusFromAABB(aabb);
	}
	
	virtual void visitRenderables(Ogre::Renderable::Visitor* visitor, bool debugRenderables) { visitor->visit(this, 0, false); }
};

/**
 * This is the base figure type which merges Ogre renderable objects with the renderer interface types. It inherits from 
 * the template parameter F which must be Figure or one of its subtypes. The parameter T must be OgreBaseRenderable or
 * one of its subtypes, an internal instance of this type is used to represent the rendering operation of the object.
 * This combination of inheritance and delegation is used to route around the need to convergent inheritance in subtypes.
 * If this type were defined to inherit from Figure then any type inheriting from it which also want to inherit from a 
 * subtype of Figure to implement that interface would then inherit Figure twice. This would require virtual inheritance
 * which doesn't play nice with the Python binding layer.
 */
template<typename T,typename F> // T <: OgreBaseRenderable, F <: Figure
class OgreBaseFigure : public F
{
protected:
	T* obj; /// The OgreBaseRenderable object which implements the actual rendering operations
	Ogre::SceneNode *node;
	OgreRenderScene *scene;
	
public:
	OgreBaseFigure(T* obj,Ogre::SceneNode *node, OgreRenderScene *scene) : obj(obj),node(node),scene(scene) { if(obj) obj->setParentObjects(this,scene); } 

	virtual ~OgreBaseFigure() { destroySceneNode(node,obj,scene); }
	
	T* getRenderable() const { return obj; }
	
	virtual const char* getName() { return obj->getName().c_str(); }
	virtual void setPosition(const vec3& v) { node->setPosition(convert(v)); }
	virtual void setRotation(const rotator& r) { node->setOrientation(convert(r)); }
	virtual void setScale(const vec3 &v) { node->setScale(convert(v)); }
	
	virtual void setMaterial(const char* mat) throw(RenderException) { obj->setMaterial(mat); }

	virtual const char* getMaterial() const 
	{ 
		Ogre::MaterialPtr mat=obj->getMaterial(); 
		return mat.isNull() ? "" : mat->getName().c_str(); 
	}

	virtual std::pair<vec3,vec3> getAABB() const
	{
		Ogre::AxisAlignedBox aabb=obj->getBoundingBox();
		return std::pair<vec3,vec3>(convert(aabb.getMinimum()),convert(aabb.getMaximum()));
	}

	virtual void setParent(Figure *fig) { setNodeFigParent(node,fig,scene); } 

	void setCameraVisibility(const Camera* cam, bool isVisible)
	{
		OgreRenderTypes::setCameraVisibility(cam,obj,isVisible,scene);
	} 

	void setVisible(bool isVisible)
	{
		if(obj && node->numAttachedObjects()==0)
			node->attachObject(obj);

		node->setVisible(isVisible);
	} 
	
	virtual bool isVisible() const { return obj && obj->isVisible(); }

	virtual bool isTransparent() const
	{
		return getRenderQueue()==Ogre::RENDER_QUEUE_6;
	}
	
	virtual bool isOverlay() const
	{
		return getRenderQueue()==Ogre::RENDER_QUEUE_OVERLAY;
	}
	
	virtual void setTransparent(bool isTrans)
	{
		setRenderQueue(isTrans ? Ogre::RENDER_QUEUE_6 : Ogre::RENDER_QUEUE_MAIN);
	}
	
	virtual void setOverlay(bool isOverlay)
	{
		setRenderQueue(isOverlay ? Ogre::RENDER_QUEUE_OVERLAY : Ogre::RENDER_QUEUE_MAIN);
	}

	virtual void setRenderQueue(sval queue)
	{
		if(queue<=Ogre::RENDER_QUEUE_MAX)
			obj->setRenderQueueGroup((Ogre::uint8)queue);
	}
	virtual sval getRenderQueue() const { return obj->getRenderQueueGroup(); }
	
	virtual vec3 getPosition(bool isDerived=false) const 
	{ 
		Ogre::Vector3 v=node->getPosition();
		
		if(isDerived){
			node->needUpdate();
			v=node->_getDerivedPosition();
		}
		
		return convert(v); 
	}
	
	virtual vec3 getScale(bool isDerived=false) const 
	{ 
		Ogre::Vector3 v=node->getScale();
		
		if(isDerived){
			node->needUpdate();
			v=node->_getDerivedScale();
		}
		
		return convert(v);
	}
	
	virtual rotator getRotation(bool isDerived=false) const 
	{ 
		Ogre::Quaternion q=node->getOrientation();
		
		if(isDerived){
			node->needUpdate();
			q=node->_getDerivedOrientation();
		}
		
		return convert(q);
	}

};

class DLLEXPORT OgreFigure : public OgreBaseFigure<OgreBaseRenderable,Figure>
{
protected:
	FigureType type;

public:
	OgreFigure(const std::string& name,const std::string & matname,OgreRenderScene *scene,FigureType type) throw(RenderException);

	virtual ~OgreFigure(){}
	
	virtual void fillData(const VertexBuffer* vb, const IndexBuffer* ib,bool deferFill=false,bool doubleSided=false) throw(RenderException) ;
};

class DLLEXPORT OgreBBSetFigure : public BBSetFigure
{
protected:
	typedef std::vector<Ogre::BillboardSet*> bbsetlist;
	static const size_t SETSIZE=10000;
	
	Ogre::SceneNode *node;
	OgreRenderScene *scene;
	std::string matname;
	FigureType type;
	bool isInitialized;
	
	const VertexBuffer* tempvb;
	bool deleteTemp;

	bbsetlist sets;
	std::string name;

	real width;
	real height;
	
	Mutex mutex;

public:
	OgreBBSetFigure(const std::string & name,const std::string & matname,OgreRenderScene *scene,FigureType type) throw(RenderException);
	
	virtual ~OgreBBSetFigure();

	virtual void setParent(Figure *fig)
	{
		setNodeFigParent(node,fig,scene);
	}

	virtual const char* getName() { return name.c_str(); }
	
	virtual void setMaterial(const char* mat) throw(RenderException) 
	{ 
		try{
			for(bbsetlist::iterator i=sets.begin();i!=sets.end();++i)
				(*i)->setMaterialName(mat); 
		}
		catch(Ogre::Exception &e){
			THROW_RENDEREX(e);
		}
	}

	virtual const char* getMaterial() const 
	{ 
		if(sets.size()==0)
			return "";

		Ogre::MaterialPtr mat=sets[0]->getMaterial(); 
		return mat.isNull() ? "" : mat->getName().c_str();
	}

	virtual std::pair<vec3,vec3> getAABB() const
	{
		vec3 minv,maxv;

		if(sets.size()>0){
			Ogre::AxisAlignedBox aabb=sets[0]->getBoundingBox();
			for(size_t i=1;i<sets.size();i++)
				aabb=aabb.intersection(sets[i]->getBoundingBox());

			minv=convert(aabb.getMinimum());
			maxv=convert(aabb.getMaximum());
		}

		return std::pair<vec3,vec3>(minv,maxv);
	}
	
	virtual void commit();

	virtual void fillData(const VertexBuffer* vb, const IndexBuffer* ib,bool deferFill=false,bool doubleSided=false) throw(RenderException) ;

	virtual void setVisible(bool isVisible);
	
	virtual void setCameraVisibility(const Camera* cam, bool isVisible);
	
	virtual bool isVisible() const
	{
		return sets.size()>0 && sets[0]->isVisible();
	}
		
	virtual bool isTransparent() const
	{
		return getRenderQueue()==Ogre::RENDER_QUEUE_6;
	}
	
	virtual bool isOverlay() const
	{
		return getRenderQueue()==Ogre::RENDER_QUEUE_OVERLAY;
	}
	
	virtual void setTransparent(bool isTrans)
	{
		setRenderQueue(isTrans ? Ogre::RENDER_QUEUE_6 : Ogre::RENDER_QUEUE_MAIN);
	}
	
	virtual void setOverlay(bool isOverlay)
	{
		setRenderQueue(isOverlay ? Ogre::RENDER_QUEUE_OVERLAY : Ogre::RENDER_QUEUE_MAIN);
	}

	virtual void setRenderQueue(sval queue)
	{
		if(queue<=Ogre::RENDER_QUEUE_MAX)
			for(bbsetlist::iterator i=sets.begin();i!=sets.end();++i)
				(*i)->setRenderQueueGroup((Ogre::uint8)queue);
	}
	virtual sval getRenderQueue() const { return sets.size()>0 ? sets[0]->getRenderQueueGroup() : 0; }

	virtual void setDimension(real width, real height)
	{
		this->width=width;
		this->height=height;
		for(bbsetlist::iterator i=sets.begin();i!=sets.end();++i)
			(*i)->setDefaultDimensions(width,height);
	}
	
	virtual real getWidth() const { return width; }
	virtual real getHeight() const { return height; }

	virtual void setUpVector(const vec3& v)
	{
		for(bbsetlist::iterator i=sets.begin();i!=sets.end();++i)
			(*i)->setCommonUpVector(convert(v));
	}

	virtual int numBillboards() const 
	{
		int count=0;
		for(bbsetlist::const_iterator i=sets.begin();i!=sets.end();++i)
			count+=(*i)->getNumBillboards();
		
		return count;
	}

	virtual void setBillboardPos(indexval index, const vec3& pos) throw(IndexException) 
	{
		Ogre::Billboard *b=getBillboard(index);
		b->mPosition=convert(pos);
	}

	virtual void setBillboardDir(indexval index, const vec3& dir) throw(IndexException) 
	{
		Ogre::Billboard *b=getBillboard(index);
		b->mDirection=convert(dir);
	}

	virtual void setBillboardColor(indexval index, const color& col) throw(IndexException) 
	{
		Ogre::Billboard *b=getBillboard(index);
		b->mColour=convert(col);
	}
	
	virtual void setPosition(const vec3& v) { node->setPosition(convert(v)); }
	virtual void setRotation(const rotator& r) { node->setOrientation(convert(r)); }
	virtual void setScale(const vec3 &v) { node->setScale(convert(v)); }	
	
	virtual vec3 getPosition(bool isDerived=false) const 
	{ 
		Ogre::Vector3 v=node->getPosition();
		
		if(isDerived){
			node->needUpdate();
			v=node->_getDerivedPosition();
		}
		
		return convert(v); 
	}
	
	virtual vec3 getScale(bool isDerived=false) const 
	{ 
		Ogre::Vector3 v=node->getScale();
		
		if(isDerived){
			node->needUpdate();
			v=node->_getDerivedScale();
		}
		
		return convert(v);
	}
	
	virtual rotator getRotation(bool isDerived=false) const 
	{ 
		Ogre::Quaternion q=node->getOrientation();
		
		if(isDerived){
			node->needUpdate();
			q=node->_getDerivedOrientation();
		}
		
		return convert(q);
	}
	
protected:
	void createBBSet();
	
	Ogre::Billboard* getBillboard(indexval index) const throw(IndexException) {
		for(bbsetlist::const_iterator i=sets.begin();index<(indexval)numBillboards() && i!=sets.end();++i)
			if(index<(indexval)(*i)->getNumBillboards())
				return (*i)->getBillboard(index);
			else
				index-=(*i)->getNumBillboards();
			
		throw IndexException("index",index,numBillboards());
	}
};

class DLLEXPORT OgreRibbonFigure : public RibbonFigure, public Ogre::RenderObjectListener
{
protected:
	Ogre::BillboardChain *bbchain;
	Ogre::SceneNode *node;
	OgreRenderScene *scene;
	std::string matname;
	std::string name;
	vec3 orient;
	
	const VertexBuffer* tempvb;
	const IndexBuffer* tempib;
	bool deleteTemp;
	
	Mutex mutex;

public:
	OgreRibbonFigure(const std::string & name,const std::string & matname,OgreRenderScene *scene) throw(RenderException);
	virtual ~OgreRibbonFigure();

	virtual void setParent(Figure *fig)
	{
		setNodeFigParent(node,fig,scene);
	}

	virtual void notifyRenderSingleObject(Ogre::Renderable* rend, const Ogre::Pass* pass, const Ogre::AutoParamDataSource* source, 
			const Ogre::LightList* pLightList, bool suppressRenderStateChanges)
	{
		if(isVisible())
			setOrientation(orient);
	}

	virtual const char* getName() { return name.c_str(); }
	
	virtual void setMaterial(const char* mat) throw(RenderException) 
	{ 
		try{
			bbchain->setMaterialName(mat); 
		}
		catch(Ogre::Exception &e){
			THROW_RENDEREX(e);
		}
	}

	virtual const char* getMaterial() const 
	{ 
		Ogre::MaterialPtr mat=bbchain->getMaterial(); 
		return mat.isNull() ? "" : mat->getName().c_str();
	}

	virtual std::pair<vec3,vec3> getAABB() const
	{
		Ogre::AxisAlignedBox aabb=bbchain->getBoundingBox();
		return std::pair<vec3,vec3>(convert(aabb.getMinimum()),convert(aabb.getMaximum()));
	}

	virtual void commit();
	
	virtual void fillData(const VertexBuffer* vb, const IndexBuffer* ib,bool deferFill=false,bool doubleSided=false) throw(RenderException);

	virtual void setVisible(bool isVisible)
	{
		node->setVisible(isVisible);
	}
	
	virtual void setCameraVisibility(const Camera* cam, bool isVisible);
	
	virtual bool isVisible() const { return bbchain->isVisible(); }

	virtual bool isTransparent() const
	{
		return getRenderQueue()==Ogre::RENDER_QUEUE_6;
	}
	
	virtual bool isOverlay() const
	{
		return getRenderQueue()==Ogre::RENDER_QUEUE_OVERLAY;
	}
	
	virtual void setTransparent(bool isTrans)
	{
		setRenderQueue(isTrans ? Ogre::RENDER_QUEUE_6 : Ogre::RENDER_QUEUE_MAIN);
	}
	
	virtual void setOverlay(bool isOverlay)
	{
		setRenderQueue(isOverlay ? Ogre::RENDER_QUEUE_OVERLAY : Ogre::RENDER_QUEUE_MAIN);
	}

	virtual void setRenderQueue(sval queue)
	{
		if(queue<=Ogre::RENDER_QUEUE_MAX)
			bbchain->setRenderQueueGroup((Ogre::uint8)queue);
	}

	virtual sval getRenderQueue() const { return bbchain->getRenderQueueGroup(); }

	virtual void setPosition(const vec3& v) { node->setPosition(convert(v)); }
	virtual void setRotation(const rotator& r) { node->setOrientation(convert(r)); }
	virtual void setScale(const vec3 &v) { node->setScale(convert(v)); }	
	
	virtual vec3 getPosition(bool isDerived=false) const 
	{ 
		Ogre::Vector3 v=node->getPosition();
		
		if(isDerived){
			node->needUpdate();
			v=node->_getDerivedPosition();
		}
		
		return convert(v); 
	}
	
	virtual vec3 getScale(bool isDerived=false) const 
	{ 
		Ogre::Vector3 v=node->getScale();
		
		if(isDerived){
			node->needUpdate();
			v=node->_getDerivedScale();
		}
		
		return convert(v);
	}
	
	virtual rotator getRotation(bool isDerived=false) const 
	{ 
		Ogre::Quaternion q=node->getOrientation();
		
		if(isDerived){
			node->needUpdate();
			q=node->_getDerivedOrientation();
		}
		
		return convert(q);
	}

	virtual void setOrientation(const vec3& orient) 
	{
		this->orient=orient;
		bbchain->setFaceCamera(orient.isZero(),convert(orient));
	}

	virtual bool isCameraOriented() const { return !orient.isZero(); }

	virtual vec3 getOrientation() const { return orient; }

	virtual void setNumRibbons(sval num) 
	{
		bbchain->setNumberOfChains(num);
	}

	virtual sval numRibbons() const { return bbchain->getNumberOfChains(); }

	virtual sval numNodes(sval ribbon) const throw(IndexException) 
	{ 
		if(ribbon>=numRibbons())
			throw IndexException("ribbon",ribbon,numRibbons());

		return bbchain->getNumChainElements(ribbon); 
	}

	virtual void setMaxNodes(sval num) 
	{ 
		bbchain->setMaxChainElements(num); 
	}

	virtual sval getMaxNodes() 
	{ 
		return bbchain->getMaxChainElements(); 
	}
	
	virtual void clearRibbons() 
	{
		bbchain->clearAllChains();
	}

	virtual void removeRibbon(sval ribbon) throw(IndexException) 
	{
		if(ribbon>=numRibbons())
			throw IndexException("ribbon",ribbon,numRibbons());

		bbchain->clearChain(ribbon);
	}

	virtual void removeNode(sval ribbon) throw(IndexException) 
	{
		if(ribbon>=numRibbons())
			throw IndexException("ribbon",ribbon,numRibbons());

		bbchain->removeChainElement(ribbon);
	}

	virtual void addNode(sval ribbon,const vec3& pos, const color& col,real width, const rotator& rot=rotator(), real tex=0.0) throw(IndexException) 
	{
		if(ribbon>=numRibbons())
			throw IndexException("ribbon",ribbon,numRibbons());

		Ogre::BillboardChain::Element elem(convert(pos),width,tex,convert(col),convert(rot));
		bbchain->addChainElement(ribbon,elem);
	}

	virtual void setNode(sval ribbon,sval node,const vec3& pos, const color& col,real width, const rotator& rot=rotator(), real tex=0.0) throw(IndexException) 
	{
		if(ribbon>=numRibbons())
			throw IndexException("ribbon",ribbon,numRibbons());

		if(node>=numNodes(ribbon))
			throw IndexException("node",node,numNodes(ribbon));

		Ogre::BillboardChain::Element elem(convert(pos),width,tex,convert(col),convert(rot));
		bbchain->updateChainElement(ribbon,node,elem);
	}

	virtual vec3 getNode(sval ribbon,sval node) throw(IndexException) 
	{ 
		if(ribbon>=numRibbons())
			throw IndexException("ribbon",ribbon,numRibbons());

		if(node>=numNodes(ribbon))
			throw IndexException("node",node,numNodes(ribbon));

		const Ogre::BillboardChain::Element &elem=bbchain->getChainElement(ribbon,node);
		return convert(elem.position);
	}

	virtual quadruple<color,real,rotator,real> getNodeProps(sval ribbon,sval node) throw(IndexException) 
	{ 
		if(ribbon>=numRibbons())
			throw IndexException("ribbon",ribbon,numRibbons());

		if(node>=numNodes(ribbon))
			throw IndexException("node",node,numNodes(ribbon));

		const Ogre::BillboardChain::Element &elem=bbchain->getChainElement(ribbon,node);

		return quadruple<color,real,rotator,real>(convert(elem.colour),elem.width,convert(elem.orientation),elem.texCoord); 
	}
};

class OgreTextureVolumeFigure;

class TextureVolumeRenderable : public OgreBaseRenderable
{
	OgreTextureVolumeFigure *fig;
	rotator lastCamRot;
	bool cameraMoved;
	
	real heights[8];
	intersect bbintersects[6]; // stores the plane intersections with the bound box as index pairs plus xi value 
	planevert interpts[6]; // stores the vertices where the plane intersects the bound box, which defines a (3,4,5,or 6)-sided polygon
	
	Matrix<OgreBaseRenderable::Vertex> vertices; // temporary store for calculated plane vertices
	IndexMatrix indices; // temporary store for calculated plane triangle indices

public:
	TextureVolumeRenderable(const std::string &name,const std::string & matname,OgreTextureVolumeFigure *fig,Ogre::SceneManager *mgr)
		: OgreBaseRenderable(name,matname,Ogre::RenderOperation::OT_TRIANGLE_LIST ,mgr), 
		fig(fig),vertices("tprverts",0,1,false), indices("tprinds",0,3,false)
	{
		depthSorting=false;
	}

	virtual ~TextureVolumeRenderable() {}
		
	virtual void _updateRenderQueue(Ogre::RenderQueue* queue); 
	virtual void _notifyCurrentCamera(Ogre::Camera* cam);

	std::pair<sval,planevert*> getPlaneIntersects(vec3 planept,vec3 planenorm);
};

class DLLEXPORT OgreTextureVolumeFigure : public OgreBaseFigure<TextureVolumeRenderable,TextureVolumeFigure>
{
	sval numplanes;
	real alpha;

	vec3 bbminv;
	vec3 bbmaxv;
	vec3 bbcenter;
	real bbradius;

	vec3 boundcube[8]; // bound box cube, not axis aligned
	vec3 texcube[8]; // tex coordinates for each corner of the volume, axis-aligned in uvw space
	
	Ogre::RGBA vertexcol;

	void setCube(vec3 *cube,const vec3& minv, const vec3& maxv)
	{
		cube[0]=minv;
		cube[7]=maxv;
		cube[1]=vec3(maxv.x(),minv.y(),minv.z());
		cube[2]=vec3(minv.x(),maxv.y(),minv.z());
		cube[3]=vec3(maxv.x(),maxv.y(),minv.z());
		cube[4]=vec3(minv.x(),minv.y(),maxv.z());
		cube[5]=vec3(maxv.x(),minv.y(),maxv.z());
		cube[6]=vec3(minv.x(),maxv.y(),maxv.z());
	}

public:
	friend class TextureVolumeRenderable;

	OgreTextureVolumeFigure(const std::string &name,const std::string & matname,OgreRenderScene *scene) ;
	
	virtual ~OgreTextureVolumeFigure() {}
	
	virtual void setNumPlanes(sval num){ numplanes=_max<sval>(1,num);}
	virtual sval getNumPlanes() const { return numplanes; }
	
	virtual real getAlpha() const { return alpha;}
	virtual void setAlpha(real a) 
	{ 
		alpha=a;
		Ogre::RenderSystem* rs=Ogre::Root::getSingleton().getRenderSystem();
		rs->convertColourValue(Ogre::ColourValue(1.0f,1.0f,1.0f,alpha),&vertexcol);
	}

	virtual void setTexAABB(const vec3& minv, const vec3& maxv) 
	{
		setCube(texcube,minv,maxv);
	}

	virtual void setAABB(const vec3& minv, const vec3& maxv) 
	{ 
		if(minv.distTo(maxv)>0){ 
			bbminv=minv; 
			bbmaxv=maxv;
			setCube(boundcube,minv,maxv);
			bbcenter=(maxv+minv)*0.5;
			bbradius=bbmaxv.distTo(bbcenter);

			vec3 minv1=minv, maxv1=maxv;
			minv1.setMinVals(maxv);
			maxv1.setMaxVals(minv);
			obj->setBoundingBox(minv1,maxv1); 
			node->needUpdate();
		} 
	}

	virtual vec3 getTexXiPos(vec3 pos) const 
	{
		vec3 tpos=getTransform().inverse()*pos;
		vec3 relpos=lerpXi<vec3>(tpos,bbminv,bbmaxv);

		return lerp<vec3,vec3>(relpos,texcube[0],texcube[7]);
	}

	virtual vec3 getTexXiDir(vec3 pos) const 
	{
		return ((getTransform().directional().inverse()*pos)*(bbmaxv-bbminv)).norm();
	}

	virtual sval getPlaneIntersects(vec3 planept, vec3 planenorm,vec3 buffer[6][2],bool transformPlane=false,bool isXiPoint=false)
	{
		transform t=getTransform(true);
		
		if(transformPlane){
			transform tinv=t.inverse();
			planept=tinv*planept;
			planenorm=tinv.directional()*planenorm;
		}
		else if(isXiPoint){
			real coeffs[8];
			basis_Hex1NL(planept.x(),planept.y(),planept.z(),coeffs);
			planept=vec3();
			for(sval i=0;i<8;i++)
				planept=planept+boundcube[i]*coeffs[i];
		}

		std::pair<sval,planevert*> result= obj->getPlaneIntersects(planept,planenorm.norm());

		for(sval i=0;i<result.first;i++){
			buffer[i][0]=transformPlane ? result.second[i].first*t : result.second[i].first;
			buffer[i][1]=result.second[i].second;
		}

		return result.first;
	}
};

class DLLEXPORT OgreGlyphFigure : public OgreBaseFigure<OgreBaseRenderable,GlyphFigure>
{
	typedef triple<const Vec3Matrix*, const Vec3Matrix*, const IndexMatrix*> glyphmesh;
	typedef std::map<std::string,glyphmesh> glyphmap; 

	std::string glyphname;
	glyphmap glyphs;
	vec3 glyphscale;

	static void fillDefaultGlyphs(glyphmap &map);

public:
	OgreGlyphFigure(const std::string& name,const std::string & matname,OgreRenderScene *scene) throw(RenderException);
	virtual ~OgreGlyphFigure(){}
	
	virtual void fillData(const VertexBuffer* vb, const IndexBuffer* ib,bool deferFill=false,bool doubleSided=false) throw(RenderException);

	virtual void setGlyphScale(vec3 v) { glyphscale=v; }
	virtual vec3 getGlyphScale() const { return glyphscale; }
	virtual void setGlyphName(const std::string& name) 
	{ 
		if(glyphs.find(name)!=glyphs.end()) 
			glyphname=name;
	}

	virtual std::string getGlyphName() const {return glyphname; }

	virtual void addGlyphMesh(const std::string& name,const Vec3Matrix* nodes,const Vec3Matrix* norms, const IndexMatrix* inds) 
	{
		glyphmap::iterator i=glyphs.find(name);

		if(i!=glyphs.end()){
			delete (*i).second.first;
			delete (*i).second.second;
			delete (*i).second.third;
		}

		glyphs[name]=glyphmesh(nodes->clone(),norms->clone(),inds->clone());
	}
};

class TextRenderable : public OgreBaseRenderable
{
	struct TextVertex
	{
		float x,y,z,u,v;
		void set(float _x, float _y, float _u, float _v,vec3& min, vec3& max)
		{
			x=_x;
			y=_y;
			z=0;
			u=_u;
			v=_v;
			vec3 v(x,y);
			min.setMinVals(v);
			max.setMaxVals(v);
		}
	};
	
public:
	std::string text;
	std::string fontname;
	std::string internalMatName;
	color col;
	VAlignType valign;
	HAlignType halign;
	real textHeight;
	real spaceWidth;
	
	bool updateCols;
	bool updateGeom;
	bool isOverlay;
	
	Ogre::HardwareVertexBufferSharedPtr colBuf;
	
	Ogre::Font *fontobj;
	
	Ogre::SceneNode *subnode;
	
	TextRenderable(const std::string &name,Ogre::SceneManager *mgr):
		OgreBaseRenderable(name,"BaseWhite",Ogre::RenderOperation::OT_TRIANGLE_LIST ,mgr),isOverlay(false),
		updateCols(true), updateGeom(true),valign(V_TOP), halign(H_LEFT),textHeight(1.0),spaceWidth(0),
		fontname("DefaultFont"),fontobj(NULL),text("<NULL>")
	{
		movableType="MovableText";
		internalMatName=name+"TextMat";
		colBuf.setNull();
		setBoundingBox(vec3(),vec3(1)); // need to have a non-zero bound box to be visible
	}
	
	virtual ~TextRenderable()
	{
		if(!mat.isNull() && mat->getName()==internalMatName)
			Ogre::MaterialManager::getSingletonPtr()->remove(mat->getName());
	}
	
	virtual void setOverlay(bool isOverlay)
	{
		this->isOverlay=isOverlay;
		if(!mat.isNull()){
			mat->setDepthBias(1.0,1.0);
			mat->setDepthCheckEnabled(!isOverlay);
			mat->setDepthWriteEnabled(isOverlay);
        }
	}
	
	virtual void setFont(const std::string& fontname) throw(RenderException);
	
protected:
	// binding index values
	static const short POS_TEX_BINDING=0;
	static const short COLOUR_BINDING=1;
	
	void updateColors();
	void updateGeometry();
	
	virtual void _notifyCurrentCamera(Ogre::Camera *cam);
	virtual void _updateRenderQueue(Ogre::RenderQueue* queue);
	
	virtual void visitRenderables(Ogre::Renderable::Visitor* visitor, bool debugRenderables){} // Add to build on Shoggoth (?)
};

// adapted from the MovableText type in http://www.ogre3d.org/tikiwiki/tiki-index.php?page=MovableText
class DLLEXPORT OgreTextFigure : public OgreBaseFigure<TextRenderable,TextFigure>
{
public:
	OgreTextFigure(const std::string& name,OgreRenderScene *scene) throw(RenderException);
	virtual ~OgreTextFigure() {}
	
	virtual void setText(const std::string& text) { obj->text=text.size() ? text : "<NULL>"; obj->updateGeom=true; }
	virtual void setFont(const std::string& fontname) throw(RenderException) { obj->setFont(fontname);}
	virtual void setColor(const color& col) { obj->col=col; obj->updateCols=true; }
	
	virtual void setVAlign(VAlignType align){ obj->valign=align;  obj->updateGeom=true; }
	virtual void setHAlign(HAlignType align){ obj->halign=align;  obj->updateGeom=true; }
	virtual void setTextHeight(real height){ obj->textHeight=height;  obj->updateGeom=true; }
	virtual void setSpaceWidth(real width) { obj->spaceWidth=width;  obj->updateGeom=true; }
	
	virtual std::string getText() const { return obj->text;}
	virtual std::string getFont() const { return obj->fontname;}
	virtual color getColor() const { return obj->col; }
	
	virtual VAlignType getVAlign() const { return obj->valign; }
	virtual HAlignType getHAlign() const { return obj->halign; }
	virtual real getTextHeight() const { return obj->textHeight; }
	virtual real getSpaceWidth() const { return obj->spaceWidth; }
	
	//virtual void setMaterial(const std::string &m) throw(RenderException)
	//{} // do not accept externally applied materials, this will mess up the internal material used to present text textures
	
	virtual void setOverlay(bool isOverlay)
	{
		OgreBaseFigure::setOverlay(isOverlay);
		obj->setOverlay(isOverlay);
	}
};

/**
 * This adapts Ogre::Texture objects to the renderer interface. It uses an internal data buffer to fill with pixel data which is
 * written to the actual texture only at render type using a CommitOp object. 
 */
class DLLEXPORT OgreTexture : public Texture
{
protected:
	/// The root scene which renders this object
	OgreRenderScene *scene;
	
	std::string filename;
	Ogre::TexturePtr ptr;
	u8* buffer;
	size_t sizeBytes;
	
public:
	OgreTexture(Ogre::TexturePtr ptr,const char *filename,OgreRenderScene *scene): 
		ptr(ptr),filename(filename), scene(scene),buffer(0),sizeBytes(ptr->getBuffer()->getSizeInBytes())
	{}

	virtual ~OgreTexture();
	
	virtual void commit();
	
	virtual Ogre::PixelBox getPixelBuffer()
	{
		if(!buffer)
			buffer=new u8[sizeBytes];
		
		return Ogre::PixelBox(ptr->getWidth(),ptr->getHeight(),ptr->getDepth(),ptr->getFormat(),buffer);
	}

	virtual const char* getFilename() const {return filename.c_str();}
	virtual const char* getName() const { return ptr->getName().c_str(); }
	virtual sval getWidth() const { return sval(ptr->getWidth());}
	virtual sval getHeight() const { return sval(ptr->getHeight());}
	virtual sval getDepth() const { return sval(ptr->getDepth());}
	virtual bool hasAlpha() const {return ptr->hasAlpha();}

	virtual TextureFormat getFormat() const
	{
		switch(ptr->getFormat()){
			case Ogre::PF_R8G8B8A8:
				return TF_RGBA32;
			case Ogre::PF_R8G8B8:
				return TF_RGB24;
			case Ogre::PF_A8:
				return TF_ALPHA8;
			case Ogre::PF_L8:
				return TF_LUM8;
			case Ogre::PF_L16:
				return TF_LUM16;
			case Ogre::PF_A4L4:
				return TF_ALPHALUM8;
			default:
				return TF_UNKNOWN;
		}
	}

	virtual void fillBlack();
	virtual void fillColor(color col);
	virtual void fillColor(const ColorMatrix *mat,indexval depth) ;
	virtual void fillColor(const RealMatrix *mat,indexval depth,real minval=0.0,real maxval=1.0, const Material* colormat=NULL,const RealMatrix *alphamat=NULL,bool mulAlpha=true) ;
};

class DLLEXPORT OgreGPUProgram : public GPUProgram
{
	OgreRenderScene *scene;
	
	Ogre::HighLevelGpuProgramPtr ptrProgram;

	std::string name;
	std::string namecounted;
	std::string language;
	std::string source;
	ProgramType ptype;
	sval createCount;
	bool hasCompileError;
	
	void createProgram()
	{
		std::ostringstream out;
		out << name << "|" << createCount;
		namecounted=out.str();
		createCount++;

		ptrProgram=Ogre::HighLevelGpuProgramManager::getSingleton().createProgram(
			namecounted, Ogre::ResourceGroupManager::DEFAULT_RESOURCE_GROUP_NAME,
			language, convert(ptype));
	}

	void setAutoConstants()
	{
		if(ptrProgram.isNull() || ptrProgram->hasCompileError())
			return;

		const Ogre::GpuProgramParametersSharedPtr& params=ptrProgram->getDefaultParameters();

		struct AutoParamPair { Ogre::String name; Ogre::GpuProgramParameters::AutoConstantType type; };	

		//A list of auto params that might be present in the shaders generated
		static const AutoParamPair autoparams[] = {
			{ "vpWidth",			Ogre::GpuProgramParameters::ACT_VIEWPORT_WIDTH },
			{ "vpHeight",			Ogre::GpuProgramParameters::ACT_VIEWPORT_HEIGHT },
			{ "view",               Ogre::GpuProgramParameters::ACT_VIEW_MATRIX },
			{ "world",              Ogre::GpuProgramParameters::ACT_WORLD_MATRIX },
			{ "worldView",			Ogre::GpuProgramParameters::ACT_WORLDVIEW_MATRIX },
			{ "worldViewProj",		Ogre::GpuProgramParameters::ACT_WORLDVIEWPROJ_MATRIX },
			{ "invWorld",           Ogre::GpuProgramParameters::ACT_INVERSE_WORLD_MATRIX },
			{ "invProj",			Ogre::GpuProgramParameters::ACT_INVERSE_PROJECTION_MATRIX },
			{ "invView",			Ogre::GpuProgramParameters::ACT_INVERSE_VIEW_MATRIX },
			{ "flip",				Ogre::GpuProgramParameters::ACT_RENDER_TARGET_FLIPPING },
			{ "texSize",            Ogre::GpuProgramParameters::ACT_TEXTURE_SIZE },
			{ "texSizeInv",         Ogre::GpuProgramParameters::ACT_INVERSE_TEXTURE_SIZE },
			//{ "lightDiffuseColor",	Ogre::GpuProgramParameters::ACT_LIGHT_DIFFUSE_COLOUR },
			//{ "lightSpecularColor", Ogre::GpuProgramParameters::ACT_LIGHT_SPECULAR_COLOUR },
			//{ "lightFalloff",		Ogre::GpuProgramParameters::ACT_LIGHT_ATTENUATION },
			//{ "lightPos",			Ogre::GpuProgramParameters::ACT_LIGHT_POSITION_VIEW_SPACE },
			//{ "lightDir",			Ogre::GpuProgramParameters::ACT_LIGHT_DIRECTION_VIEW_SPACE },
			{ "spotParams",			Ogre::GpuProgramParameters::ACT_SPOTLIGHT_PARAMS },
			{ "farClipDistance",	Ogre::GpuProgramParameters::ACT_FAR_CLIP_DISTANCE },
			{ "shadowViewProjMat",	Ogre::GpuProgramParameters::ACT_TEXTURE_VIEWPROJ_MATRIX },
			{ "camPos",             Ogre::GpuProgramParameters::ACT_CAMERA_POSITION  },
			{ "camPosObjectSpace",  Ogre::GpuProgramParameters::ACT_CAMERA_POSITION_OBJECT_SPACE  },
			{ "depthRange",         Ogre::GpuProgramParameters::ACT_SCENE_DEPTH_RANGE }
		};

		size_t numParams = sizeof(autoparams) / sizeof(AutoParamPair);

		for (size_t i=0; i<numParams; i++)
			if (params->_findNamedConstantDefinition(autoparams[i].name))
				params->setNamedAutoConstant(autoparams[i].name, autoparams[i].type);
	}

public:
	OgreGPUProgram(const std::string& name,ProgramType ptype,OgreRenderScene *scene,const std::string& language="cg") : 
			name(name),ptype(ptype), scene(scene),language(language),source(""),namecounted(""),createCount(0),hasCompileError(false)
	{
		createProgram();

		setDefaultProfiles();
		setEntryPoint("main");
	}
	
	virtual ~OgreGPUProgram();

	virtual std::string getName() const {return name; }
	
	virtual void setType(ProgramType pt) 
	{ 
		ptype=pt;
		ptrProgram->setType(convert(pt));
		//setDefaultProfiles();
	}
	
	virtual ProgramType getType() const { return ptype; }
	virtual std::string getLanguage() const { return language; }
	virtual void setLanguage(const std::string& lang) { language=lang; }
	virtual bool hasError() const { return hasCompileError; }
	virtual std::string getSourceCode() const { return ptrProgram->getSource(); }
	virtual bool setParameter(const std::string& param, const std::string& val) { return ptrProgram->setParameter(param,val); }
	virtual std::string getParameter(const std::string& param) const 
	{ 
		Ogre::ParameterList pl=ptrProgram->getParameters();
		
		for(size_t i=0;i<pl.size();i++)
			if(pl[i].name==param)
				return ptrProgram->getParameter(pl[i].name);

		return "";
	}

	// Set the program's code to the given string. This will involve creating a new Ogre program object if this isn't the first 
	// time code has been assigned, which is necessary since programs can't be changed once compiled it seems.
	virtual void setSourceCode(const std::string& code)
	{ 
		std::string oldnamecounted=namecounted;
		bool isFirstSource=(source=="");
		std::ostringstream out;

		if(!isFirstSource){ // create a new program if this is not the first time code has been assigned
			Ogre::NameValuePairList nvp;

			const Ogre::ParameterList& params=ptrProgram->getParameters();
			for(Ogre::ParameterList::const_iterator i=params.begin();i!=params.end();i++){
				Ogre::String name=(*i).name;
				nvp[name]=ptrProgram->getParameter(name);
			}

			createProgram();

			ptrProgram->setParameterList(nvp);
		}
		
		ptrProgram->resetCompileError();
		ptrProgram->setSource(std::string(code));
		ptrProgram->load();

		if(ptrProgram->hasCompileError()){ // if we have an error set the code to be the old code
			hasCompileError=true;
			//ptrProgram->resetCompileError();
			
			if(!isFirstSource){ // restore old code
				ptrProgram->unload();
				ptrProgram->setSource(source); 
			}
			
			out << "GPU Program '" << name << "' compile failed (" << namecounted << ")";
		}
		else{
			setAutoConstants();
			hasCompileError=false;
			source=code; // save new code definition
			
			out << "GPU Program '" << name << "' compile succeeded (" << namecounted << ")";
		}
		
		Ogre::LogManager::getSingleton().getDefaultLog()->logMessage(out.str());

		// if a new program was created to replace the initial one, find every material that was using the initial one and swap them over
		if(!isFirstSource){
			Ogre::ResourceManager::ResourceMapIterator i= Ogre::MaterialManager::getSingleton().getResourceIterator();

			while(i.hasMoreElements()){
				Ogre::ResourcePtr p=i.getNext();
				Ogre::MaterialPtr mat=Ogre::MaterialManager::getSingleton().getByName(p->getName()); //i.getNext();
				if(mat->getNumTechniques()==0 || mat->getTechnique(0)->getNumPasses()==0)
					continue;

				Ogre::Pass* pass=mat->getTechnique(0)->getPass(0);

				switch(ptype){
				case PT_FRAGMENT: 
					if(pass->getFragmentProgramName()==oldnamecounted)
						pass->setFragmentProgram(namecounted,false);
					break;
				case PT_GEOMETRY: 
					if(pass->getGeometryProgramName()==oldnamecounted)
						pass->setGeometryProgram(namecounted,false);
					break;
				case PT_VERTEX: 
					if(pass->getVertexProgramName()==oldnamecounted)
						pass->setVertexProgram(namecounted,false);
					break;
				}    
			}

			Ogre::HighLevelGpuProgramManager::getSingleton().remove(oldnamecounted);
		}
	}

	virtual std::vector<std::string> getParameterNames() const 
	{ 
		std::vector<std::string> result; 
		
		Ogre::ParameterList pl=ptrProgram->getParameters();
		
		for(size_t i=0;i<pl.size();i++)
			result.push_back(pl[i].name);
		
		return result;
	}
	
	void setDefaultProfiles()
	{
		// arbfp1 arbvp1 fp20 fp30 fp40 glsl gp4fp gp4gp gp4vp gpu_fp gpu_gp gpu_vp nvgp4 vp30 vp40
		// hlsl ps_1_1 ps_1_2 ps_1_3 ps_1_4 ps_2_0 ps_2_a ps_2_b ps_2_x ps_3_0 vs_1_1 vs_2_0 vs_2_a vs_2_x vs_3_0

		switch(ptype){
		case PT_FRAGMENT : setProfiles("fp40 arbfp1 fp30 ps_2_x ps_2_0 ps_1_1"); break;
		case PT_GEOMETRY : setProfiles("vp40 arbvp1 vp30 vs_2_x vs_2_0 vs_1_1"); break;
		case PT_VERTEX   : setProfiles("vp40 arbvp1 vp30 vs_2_x vs_2_0 vs_1_1"); break;
		}                 
	}
};

class DLLEXPORT OgreRenderAdapter : public RenderAdapter
{
public:
	Ogre::Root *root;
	Ogre::SceneManager *mgr;
	Ogre::RenderWindow *win;
	Ogre::OverlaySystem *overlay;
	Config *config;
	
	OgreRenderScene *scene;

	OgreRenderAdapter(Config *config) throw(RenderException);
	virtual ~OgreRenderAdapter();

	virtual u64 createWindow(int width, int height) throw(RenderException);
	virtual void paint();
	virtual void resize(int x, int y,int width, int height);

	virtual RenderScene* getRenderScene();
};

class DLLEXPORT OgreRenderScene: public RenderScene
{
public:
	Ogre::Root *root;
	Ogre::SceneManager *mgr;
	Ogre::RenderWindow *win;
	Config *config;
	std::string resGroupName;
	
	Ogre::MaterialPtr background;

	typedef std::map<std::string,Ogre::SceneNode*> nodemap;

	/// Maps Figure objects to SceneNode objects created for them
	nodemap nmap;
	/// Counts how many cameras have been created and assigns a unique number to each (up to 31)
	u32 cameraCount;

	u32 assetCount;
	
	std::vector<ResourceOp*> pendingOps;
	Mutex sceneMutex;

	OgreRenderScene(OgreRenderAdapter *adapt) : root(adapt->root), mgr(adapt->mgr), win(adapt->win),config(adapt->config),cameraCount(0),assetCount(0)
	{
		resGroupName=Ogre::ResourceGroupManager::DEFAULT_RESOURCE_GROUP_NAME;
	}

	virtual ~OgreRenderScene(){}

	virtual Camera* createCamera(const char* name, real left = 0.0f, real top = 0.0f, real width = 1.0f, real height = 1.0f) throw(RenderException);
	virtual void setAmbientLight(const color & c);

	virtual void addResourceDir(const char* dir);
	
	virtual void initializeResources();

	virtual Material* createMaterial(const char* name) throw(RenderException);

	virtual Figure* createFigure(const char* name, const char* mat,FigureType type) throw(RenderException);
	
	virtual Light* createLight() throw(RenderException);

	virtual Image* loadImageFile(const std::string &filename) throw(RenderException);

	virtual Texture* createTexture(const char* name,sval width, sval height, sval depth, TextureFormat format) throw(RenderException);

	virtual Texture* loadTextureFile(const char* name,const char* absFilename) throw(RenderException);
	
	virtual GPUProgram* createGPUProgram(const char* name,ProgramType ptype,const char* language) throw(RenderException);
	
	virtual void saveScreenshot(const char* filename,Camera* c=NULL,int width=0,int height=0,real stereoOffset=0.0,TextureFormat tf=TF_RGB24) throw(RenderException);
	
	virtual Config* getConfig() const { return config; }

	/// Iterate over all queued ResourceOp objects, calling their op() method, deleting them, and clearing the queue
	virtual void applyResourceOps()
	{
		critical(&sceneMutex){
			for(std::vector<ResourceOp*>::iterator i=pendingOps.begin();i!=pendingOps.end();++i){
				(*i)->op();
				delete *i;
			}
			
			pendingOps.clear();
		}
	}
	
	/// Add the resource operation to the queue, this assigns responsibility to delete `op' to the OgreRenderScene object
	virtual void addResourceOp(ResourceOp *op)
	{
		critical(&sceneMutex){
			pendingOps.push_back(op);
		}
	}
	
	/// Remove operations with the given parent name from the queue
	virtual void removeResourceOp(std::string parentname)
	{
		critical(&sceneMutex){
			for(std::vector<ResourceOp*>::iterator i=pendingOps.begin();i!=pendingOps.end();)
				if((*i)->parentname==parentname){
					delete *i;
					pendingOps.erase(i);
				}
				else
					++i;
		}
	}

	virtual void logMessage(const char* msg)
	{
		Ogre::LogManager::getSingleton().getDefaultLog()->logMessage(msg);
	}

	virtual void setBGObject(color col,bool enabled)
	{
		if(background.isNull())
			background=Ogre::MaterialManager::getSingleton().create("background", Ogre::ResourceGroupManager::DEFAULT_RESOURCE_GROUP_NAME, false);
		
		background->setAmbient(0,0,0);
		background->setDiffuse(0,0,0,0);
		background->setSelfIllumination(convert(col));
		//background->setLightingEnabled(false);
		mgr->setSkyBox(enabled,background->getName(),1000);
	}
	
	virtual Ogre::SceneNode* createNode(const std::string& name)
	{
		critical(&sceneMutex){ // used to ensure a nodes cannot be created, queried, or deleted simultaneously
			Ogre::SceneNode* node=mgr->getRootSceneNode()->createChildSceneNode();
			nmap[name]=node;
			return node;
		}
	}

	virtual Ogre::SceneNode* getNode(Figure *fig)
	{
		critical(&sceneMutex){ // used to ensure a nodes cannot be created, queried, or deleted simultaneously
			std::string name=fig->getName();
			if(nmap.find(name)!=nmap.end())
				return nmap[name];
			else
				return NULL;
		}
	}

	virtual void destroyNode(Ogre::SceneNode *node) throw(Ogre::InternalErrorException)
	{
		critical(&sceneMutex){ // used to ensure a nodes cannot be created, queried, or deleted simultaneously
			std::string  name="";
			for(nodemap::iterator it=nmap.begin();!name.size() && it!=nmap.end();++it)
				if(it->second==node)
					name=it->first;
				
			if(name.size()){
				nmap.erase(name);
				mgr->destroySceneNode(node);
			}
			else
				OGRE_EXCEPT(Ogre::Exception::ERR_INTERNAL_ERROR,"Cannot find Figure for node","OgreRenderScene::destroyNode");
		}
	}

	std::string getUniqueEntityName(const std::string& name);
	
	std::string getUniqueFigureName(const std::string& name);

	std::string getUniqueResourceName(const std::string& name, Ogre::ResourceManager& rmgr) throw(Ogre::InternalErrorException);
};


} // namespace OgreRenderTypes
#endif /* RENDERSCENE_H_ */

