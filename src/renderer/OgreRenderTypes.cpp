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

#include "OgreRenderTypes.h"

#include <cctype>

namespace RenderTypes
{
using namespace OgreRenderTypes;

/// Connects the Ogre3D interface implementation with the generic interface layer by instantiating the Ogre adapter object
RenderAdapter* getRenderAdapter(Config* config) throw(RenderException)
{
	return new OgreRenderAdapter(config);
}
} // namespace RenderTypes


namespace OgreRenderTypes
{
	
Ogre::HardwareBuffer::Usage OgreBaseRenderable::vertexBufferUsage=Ogre::HardwareBuffer::HBU_DYNAMIC_WRITE_ONLY;
Ogre::HardwareBuffer::Usage OgreBaseRenderable::indexBufferUsage=Ogre::HardwareBuffer::HBU_DYNAMIC_WRITE_ONLY;

void setNodeFigParent(Ogre::SceneNode* node,Figure *fig,OgreRenderScene* scene)
{
	node->getParent()->removeChild(node); // detach the node from its current parent

	if(fig==NULL) // if fig is null then set the parent to be the root node
		scene->mgr->getRootSceneNode()->addChild(node);
	else{
		Ogre::SceneNode* pnode=scene->getNode(fig); // find the node fig is attached to
		if(pnode!=NULL)
			pnode->addChild(node); // set the node to be a child of the same node as fig
	}
} 

void setCameraVisibility(const Camera* cam, Ogre::MovableObject *obj,bool isVisible,OgreRenderScene* scene)
{
	if(cam==NULL){
		u32 flag=0;
		obj->setVisibilityFlags(isVisible ? ~flag : flag);
	}
	else{
		u32 flag=dynamic_cast<const OgreCamera*>(cam)->getVisibilityMask();
		
		if(isVisible)
			obj->addVisibilityFlags(flag);
		else
			obj->removeVisibilityFlags(flag);
	}
} 

void destroySceneNode(Ogre::SceneNode *node,Ogre::MovableObject* obj,OgreRenderScene *scene)
{
	if(node){
		if(obj)
			node->detachObject(obj);
		scene->destroyNode(node);
	}
	SAFE_DELETE(obj);
}

OgreBaseRenderable::OgreBaseRenderable(const std::string& name,const std::string& matname,Ogre::RenderOperation::OperationType _opType,Ogre::SceneManager *mgr) throw(RenderException) : 
		Ogre::MovableObject(name), movableType("OgreRenderable"), vertexData(NULL), _opType(_opType), 
		indexData(NULL),_numVertices(0),_numIndices(0),localVertBuff(NULL),localIndBuff(NULL), depthSorting(true),deferFillOp(false)
{
	mat.setNull();
	vertBuf.setNull();
	
	_notifyManager(mgr);
	
	setMaterial(matname.size()==0 ? "BaseWhite" : matname.c_str());
	setVisibilityFlags(1); // set default visibility so that every camera by default sees this object
}

void OgreBaseRenderable::createBuffers(size_t numVerts,size_t numInds,bool deferCreate)
{
	deferFillOp=deferCreate;
	_numVertices=numVerts;
	_numIndices=numInds;

	if(deferCreate || (vertexData && vertexData->vertexCount==numVerts && indexData && indexData->indexCount==numInds))
		return;
	
	destroyBuffers();
	
	// create vertex data object
	vertexData = OGRE_NEW Ogre::VertexData();
	vertexData->vertexStart = 0;
	vertexData->vertexCount = _numVertices;

	// create index data object
	indexData  = OGRE_NEW Ogre::IndexData();
	indexData->indexStart = 0;
	indexData->indexCount = _numIndices;
	
	Ogre::VertexDeclaration* decl = vertexData->vertexDeclaration;
	size_t offset = 0;

	// define vertex to match OgreBaseRenderable::Vertex
	decl->addElement(0, offset, Ogre::VET_FLOAT3, Ogre::VES_POSITION);
	offset += Ogre::VertexElement::getTypeSize(Ogre::VET_FLOAT3);
	decl->addElement(0, offset, Ogre::VET_FLOAT3, Ogre::VES_NORMAL);
	offset += Ogre::VertexElement::getTypeSize(Ogre::VET_FLOAT3);
	decl->addElement(0, offset, Ogre::VET_COLOUR, Ogre::VES_DIFFUSE);
	offset += Ogre::VertexElement::getTypeSize(Ogre::VET_COLOUR);
	decl->addElement(0, offset, Ogre::VET_FLOAT3, Ogre::VES_TEXTURE_COORDINATES);
	offset += Ogre::VertexElement::getTypeSize(Ogre::VET_FLOAT3);

	Ogre::HardwareBufferManager& hbm=Ogre::HardwareBufferManager::getSingleton();
	
	// create the vertex and index buffers
	vertBuf=hbm.createVertexBuffer(decl->getVertexSize(0), _numVertices,vertexBufferUsage);
	vertexData->vertexBufferBinding->setBinding(0, vertBuf);
	indexData->indexBuffer = hbm.createIndexBuffer(Ogre::HardwareIndexBuffer::IT_32BIT, _numIndices, indexBufferUsage);
}

void OgreBaseRenderable::destroyBuffers()
{
	SAFE_DELETE(vertexData);
	SAFE_DELETE(indexData);

	vertBuf.setNull();
}

void OgreBaseRenderable::_updateRenderQueue(Ogre::RenderQueue* queue) 
{
	if(vertexData==NULL && !deferFillOp)
		return;
			
	//bool locked=false;
	trylock(&mutex,0.0001){
		//locked=true;

		if(deferFillOp){
			deferFillOp=false;
			if(_numVertices>0 || _numIndices>0){
				createBuffers(_numVertices,_numIndices); 
				commitBuffers();
				deleteLocalIndBuff();
				deleteLocalVertBuff();
			}
			else 
				fillDefaultData();
		}

		bool doSort=parent!=NULL && depthSorting && scene!=NULL && scene->getRenderHighQuality();

		if(doSort)
			doSort=getRenderQueueGroup()!=Ogre::RENDER_QUEUE_MAIN && _numIndices>2 && _opType==Ogre::RenderOperation::OT_TRIANGLE_LIST;

		// if distance sorting is set and this object stores a triangle list, sort the triangle indices by inverse distance from the camera
		if(doSort){
			typedef quadruple<real,indexval,indexval,indexval> distindex;
			typedef triple<indexval,indexval,indexval> triindex;

			size_t numtris=_numIndices/3;
			vec3 campos=parent->getTransform().inverse()*lastCamPos; 
			float cx=campos.x(),cy=campos.y(),cz=campos.z();

			distindex* distindices=new distindex[numtris];

			Vertex* vbuf=(Vertex*)vertBuf->lock(Ogre::HardwareBuffer::HBL_NORMAL);
			triindex* buf=(triindex*)indexData->indexBuffer->lock(Ogre::HardwareBuffer::HBL_NORMAL);

			for(size_t i=0;i<numtris;i++){
				indexval a=buf[i].first,b=buf[i].second,c=buf[i].third;
				float x=(vbuf[a].pos[0]+vbuf[b].pos[0]+vbuf[c].pos[0])/3.0f-cx;
				float y=(vbuf[a].pos[1]+vbuf[b].pos[1]+vbuf[c].pos[1])/3.0f-cy;
				float z=(vbuf[a].pos[2]+vbuf[b].pos[2]+vbuf[c].pos[2])/3.0f-cz;
				distindices[i]=distindex(-(x*x+y*y+z*z),a,b,c);
			}

			qsort(distindices,numtris,sizeof(distindex),sortTupleFirstCB<distindex>);

			for(size_t i=0;i<numtris;i++){
				buf[i].first=distindices[i].second;
				buf[i].second=distindices[i].third;
				buf[i].third=distindices[i].fourth;
			}

			vertBuf->unlock();
			indexData->indexBuffer->unlock();
			delete distindices;
		}
	}

	//if(!locked)
	//	fillDefaultData();

	if (mRenderQueuePrioritySet)
		queue->addRenderable(this, mRenderQueueID, mRenderQueuePriority);
	else if(mRenderQueueIDSet)
		queue->addRenderable(this, mRenderQueueID);
	else
		queue->addRenderable(this);
}

void OgreBaseRenderable::_notifyCurrentCamera(Ogre::Camera* cam)
{
	lastCamPos=convert(cam->getPosition());
}
	
void OgreBaseRenderable::getRenderOperation(Ogre::RenderOperation& op)
{
	op.operationType = _opType;
	op.useIndexes = _numIndices>0;
	op.vertexData = vertexData;
	op.indexData = _numIndices>0 ? indexData : NULL;
}

OgreBaseRenderable::Vertex* OgreBaseRenderable::getLocalVertBuff()
{
	if(localVertBuff==NULL && _numVertices>0)
		localVertBuff=new OgreBaseRenderable::Vertex[_numVertices];
	
	return localVertBuff;
}

indexval* OgreBaseRenderable::getLocalIndBuff()
{
	if(localIndBuff==NULL && _numIndices>0)
		localIndBuff=new indexval[_numIndices];
	
	return localIndBuff;
}

void OgreBaseRenderable::commitBuffers(bool commitVert, bool commitInd)
{
	if(commitVert && localVertBuff){
		void* buf=vertBuf->lock(Ogre::HardwareBuffer::HBL_NORMAL);
		memcpy(buf,localVertBuff,_numVertices*sizeof(OgreBaseRenderable::Vertex));
		vertBuf->unlock();
	}

	if(commitInd && localIndBuff){
		void* buf=indexData->indexBuffer->lock(Ogre::HardwareBuffer::HBL_NORMAL);
		memcpy(buf,localIndBuff,_numIndices*sizeof(indexval));
		indexData->indexBuffer->unlock();
	}
}

void OgreBaseRenderable::commitMatrices(const Matrix<Vertex>* verts,const IndexMatrix *inds)
{
	if(verts){
		void* buf=vertBuf->lock(Ogre::HardwareBuffer::HBL_NORMAL);
		memcpy(buf,verts->dataPtr(),verts->memSize());
		vertBuf->unlock();
	}

	if(inds){
		void* buf=indexData->indexBuffer->lock(Ogre::HardwareBuffer::HBL_NORMAL);
		memcpy(buf,inds->dataPtr(),inds->memSize());
		indexData->indexBuffer->unlock();
	}

}

void OgreBaseRenderable::fillDefaultData(bool deferFill)
{
	deferFillOp=deferFill;
	_numVertices=0;
	_numIndices=0;

	if(!deferFill){
		// the buffers need to be filled with valid data for the type of renderable this is, so choose based on _opType how many vertices and indices to create
		sval numvals=1;
		if(_opType==Ogre::RenderOperation::OT_LINE_LIST)
			numvals=2;
		else if(_opType==Ogre::RenderOperation::OT_TRIANGLE_LIST || _opType==Ogre::RenderOperation::OT_TRIANGLE_STRIP)
			numvals=3;

		createBuffers(numvals,numvals);

		memset(getLocalVertBuff(),0,sizeof(OgreBaseRenderable::Vertex)*numvals);
		memset(getLocalIndBuff(),0,sizeof(indexval)*numvals);
		
		commitBuffers(true,numvals>1); // only commit the index buffer if _opType!=Ogre::RenderOperation::OT_POINT_LIST
		deleteLocalVertBuff();
		deleteLocalIndBuff();
		setBoundingBox(vec3(),vec3(1)); // this of course isn't correct but a zero- or negative-sized box isn't acceptable
	}
}

OgreBBSetFigure::~OgreBBSetFigure()
{
	for(bbsetlist::iterator i=sets.begin();i!=sets.end();++i){
		node->detachObject(*i);
		scene->mgr->destroyBillboardSet(*i);
	}
	
	scene->destroyNode(node);
}
	
OgreCamera::~OgreCamera()
{
	scene->mgr->destroyCamera(camera);
}

OgreLight::~OgreLight()
{
	scene->mgr->destroyLight(light);
}

OgreMaterial::~OgreMaterial()
{
	Ogre::MaterialManager::getSingleton().remove(mat->getName());
	mat.setNull();
}

OgreFigure::OgreFigure(const std::string &name,const std::string & matname,OgreRenderScene *scene,FigureType type) throw(RenderException) :
		OgreBaseFigure(new OgreBaseRenderable(name,matname,convert(type),scene->mgr),scene->createNode(this),scene), type(type)
{}

void OgreFigure::fillData(const VertexBuffer* vb, const IndexBuffer* ib,bool deferFill,bool doubleSided) throw(RenderException) 
{
	try{
		critical(obj->getMutex()){
			Ogre::RenderSystem* rs=Ogre::Root::getSingleton().getRenderSystem();

			size_t indexWidth=0,indexSum=0;
			size_t numverts=vb ? vb->numVertices() : 0;
			size_t numinds=(ib && type!=FT_POINTLIST) ? ib->numIndices() : 0;
			
			if(numinds>0){
				indexWidth=ib->indexWidth(0); // NOTE: assumes all indices of the same length, this may change later?
				indexSum=indexWidth*numinds;
			}
	
			if(numverts==0){ // if there's not vertices or vb is NULL, fill with default data so that the figure is at least in a valid state
				obj->fillDefaultData(deferFill);
				node->needUpdate();
				return;
			}
			
			doubleSided=doubleSided && type==FT_TRILIST; // doubleSided is only meaningful for triangles
			size_t buffmul=doubleSided ? 2 : 1;

			obj->createBuffers(numverts*buffmul,indexSum*buffmul,deferFill); // create buffers even if indexSum is 0
			
			if(indexSum!=0 || type==FT_POINTLIST){ // do nothing when there's no indices, this will work and is useful if all elements get filtered out
				OgreBaseRenderable::Vertex *buf=obj->getLocalVertBuff();

				vec3 minv=vb->getVertex(0), maxv=vb->getVertex(0);
			
				for (sval i = 0; i < numverts; i++) {
					vec3 pos = vb->getVertex(i),norm,uvw;
					
					minv.setMinVals(pos);
					maxv.setMaxVals(pos);
	
					if(vb->hasNormal())
						norm=vb->getNormal(i);
			
					if(vb->hasUVWCoord() && type!=FT_POINTLIST)
						uvw=vb->getUVWCoord(i);
				
					pos.setBuff(buf[i].pos);
					norm.setBuff(buf[i].norm);
					uvw.setBuff(buf[i].tex);
			
					if(vb->hasColor()){
						color col=vb->getColor(i);
						rs->convertColourValue(convert(col),&buf[i].col);
					}
					else
						buf[i].col=0xffffffff;
				}

				if(doubleSided){ // clone all vertices with inverted normals
					memcpy(&buf[numverts],buf,sizeof(OgreBaseRenderable::Vertex)*numverts);

					for (size_t i = numverts; i < numverts*2; i++) {
						buf[i].norm[0]*=-1;
						buf[i].norm[1]*=-1;
						buf[i].norm[2]*=-1;
					}
				}
	
				if(numinds>0){
					indexval *ibuf=obj->getLocalIndBuff();
					size_t index=0;
	
					for (sval i = 0; i < numinds; i++)
						for (sval j = 0; j < indexWidth; j++){
							ibuf[index]=ib->getIndex(i, j);
							index++;
						}

					if(doubleSided && indexWidth==3) // generate reversed triangles
						for (sval i = 0; i < index; i+=3){
							ibuf[index+i]=ibuf[i]+indexval(numverts);
							ibuf[index+i+1]=ibuf[i+2]+indexval(numverts);
							ibuf[index+i+2]=ibuf[i+1]+indexval(numverts);
						}
			
				}

				obj->setBoundingBox(minv,maxv);
				node->needUpdate();

				if(!deferFill){
					obj->commitBuffers();
					obj->deleteLocalIndBuff();
					obj->deleteLocalVertBuff();
				}
			}
		}
	} catch(Ogre::Exception &e){
		THROW_RENDEREX(e);
	}
}

OgreTextureVolumeFigure::OgreTextureVolumeFigure(const std::string &name,const std::string & matname,OgreRenderScene *scene) :
			OgreBaseFigure(new TextureVolumeRenderable(name,matname,this,scene->mgr),scene->createNode(this),scene),numplanes(10), alpha(1.0)
{
	setAABB(vec3(0),vec3(1)); // default non-zero sized bounding box
	setTexAABB(vec3(0),vec3(1)); // default texture space, works without texture wrap around if texture addresses are clamped
}

Camera* OgreRenderScene::createCamera(const char* name, real left, real top, real width, real height) throw(RenderException)
{
	try{
		std::ostringstream os;
		os << name << "_" << cameraCount; // create a unique name based on `name' and the counter 
				
		Ogre::Camera *c = mgr->createCamera(os.str());

		Ogre::Viewport *port = win->addViewport(c,win->getNumViewports(),left,top,width,height);
		port->setBackgroundColour(Ogre::ColourValue::Black);
		port->setVisibilityMask(1); // all cameras by default have a visibility mask so that no camera is set to "see all"

		OgreCamera *oc = new OgreCamera(c, port, this,cameraCount==0 ? 0 : 1+cameraCount%31);
		cameraCount++;
		oc->setNearClip(0.001f);
		oc->setFarClip(1000000.0f);

		return oc;
	} catch(Ogre::Exception &e){
		THROW_RENDEREX(e);
	}
}

void OgreRenderScene::saveScreenshot(const char* filename, Camera* c,int width,int height,real stereoOffset,TextureFormat tf) throw(RenderException) 
{ 
	std::string fn=filename;
	if(fn.find_last_of(".")==std::string::npos)
		fn=fn+".png";

	try{
		if(c==NULL)
			win->writeContentsToFile(fn);
		else
			c->renderToFile(fn,width,height,tf,stereoOffset);
	}
	catch(Ogre::Exception &e){
		THROW_RENDEREX(e);
	}
}

void OgreRenderScene::addResourceDir(const char* dir)
{
	Ogre::ResourceGroupManager::getSingleton().addResourceLocation(dir,"FileSystem");
	//Ogre::ResourceGroupManager::getSingleton().initialiseAllResourceGroups();
}

void OgreRenderScene::initializeResources()
{
	Ogre::ResourceGroupManager::getSingleton().initialiseAllResourceGroups();
}

void OgreRenderScene::setAmbientLight(const color& c)
{
	mgr->setAmbientLight(convert(c));
}

Material* OgreRenderScene::createMaterial(const char* name) throw(RenderException)
{
	try{
		std::string uname=getUniqueResourceName(name,Ogre::MaterialManager::getSingleton());
		if(Ogre::MaterialManager::getSingleton().resourceExists(uname))
			throw RenderException("Rsource exists",__FILE__,__LINE__);

		Ogre::MaterialPtr mMat = Ogre::MaterialManager::getSingleton().create(uname, resGroupName, false);
	
		OgreMaterial *m= new OgreMaterial(mMat);
		return m;
	}
	catch(Ogre::Exception &e){
		THROW_RENDEREX(e);
	}
}

Figure* OgreRenderScene::createFigure(const char* name, const char* mat,FigureType type) throw(RenderException)
{
	try{
		Figure *f=NULL;
		std::string uname=getUniqueFigureName(name);

		if(type==FT_LINELIST || type==FT_POINTLIST || type==FT_TRILIST || type==FT_TRISTRIP)
			f=new OgreFigure(uname,mat,this,type);
		else if(type==FT_GLYPH)
			f=new OgreGlyphFigure(uname,mat,this);
		else if(type==FT_RIBBON)
			f=new OgreRibbonFigure(uname,mat,this);
		else if(type==FT_TEXVOLUME)
			f=new OgreTextureVolumeFigure(uname,mat,this);
		else if(type==FT_TEXT)
			f=new OgreTextFigure(uname,this);
		else
			f=new OgreBBSetFigure(uname,mat,this,type);
		
		return f;
	}
	catch(Ogre::Exception &e){
		THROW_RENDEREX(e);
	}
}

Light* OgreRenderScene::createLight() throw(RenderException)
{
	try{
		Ogre::Light *light=mgr->createLight();
		OgreLight* l=new OgreLight(light,this);
	
		l->setPoint();
	
		return l;
	}
	catch(Ogre::Exception &e){
		THROW_RENDEREX(e);
	}
}

Image* OgreRenderScene::loadImageFile(const std::string &filename) throw(RenderException)
{
	try{
		Ogre::String ext=filename.substr(filename.find_last_of('.')+1);

		std::ifstream in(filename.c_str(), std::ios::binary|std::ios::in);
		Ogre::DataStreamPtr istream(new Ogre::FileStreamDataStream(filename, &in, false));
		Ogre::Image img;

		img.load(istream,ext);

		in.close();

		return new OgreImage(img);
	}
	catch(Ogre::Exception &e){
		THROW_RENDEREX(e);
	}
	catch(std::exception & se){
		throw RenderException(se.what(),__FILE__,__LINE__);
	}
}

Texture* OgreRenderScene::createTexture(const char* name,sval width, sval height, sval depth, TextureFormat format) throw(RenderException)
{
	try{
		depth=_max<sval>(1,depth);
		std::string uname=getUniqueResourceName(name,Ogre::TextureManager::getSingleton());
		
		// create a texture that's always 3D even if depth==1, this is so the shaders can always work with a sampler3D object
		Ogre::TexturePtr tp=Ogre::TextureManager::getSingleton().createManual(uname,resGroupName, Ogre::TEX_TYPE_3D, width,height,depth,0,convert(format));

		return new OgreTexture(tp,"");
	}
	catch(Ogre::Exception &e){
		THROW_RENDEREX(e);
	}
}

Texture* OgreRenderScene::loadTextureFile(const char* name,const char* absFilename) throw(RenderException)
{
	try{
		Ogre::TexturePtr tp=Ogre::TextureManager::getSingleton().getByName(name,resGroupName);
		if(tp.isNull()){
			Ogre::String sname=absFilename;
			Ogre::String ext=sname.substr(sname.find_last_of('.')+1);
			
			std::ifstream in(absFilename, std::ios::binary|std::ios::in);
			Ogre::DataStreamPtr istream(new Ogre::FileStreamDataStream(absFilename, &in, false));
			Ogre::Image img;

			img.load(istream,ext);
			
			tp=Ogre::TextureManager::getSingleton().loadImage(name,resGroupName,img);
		}
		return new OgreTexture(tp,absFilename);
	}
	catch(Ogre::Exception &e){
		THROW_RENDEREX(e);
	}
}

GPUProgram* OgreRenderScene::createGPUProgram(const char* name,ProgramType ptype,const char* language) throw(RenderException)
{
	try{
		OgreGPUProgram* prog=new OgreGPUProgram(name,ptype,language!=NULL ? language : "cg");

		if(prog->hasError()){
			delete prog;
			throw RenderException("GPU Program failed to compile; check log file");
		}
		
		return prog;
	}
	catch(Ogre::Exception &e){
		THROW_RENDEREX(e);
	}
}

void OgreCamera::renderToTexture(sval width,sval height,TextureFormat format,real stereoOffset) throw(RenderException)
{
	try{
		u32 mask=port->getVisibilityMask();
		Ogre::ColourValue bg=port->getBackgroundColour();

		Ogre::RenderTarget *rt = rtt_texture.isNull() ? NULL : rtt_texture->getBuffer()->getRenderTarget();

		if(width==0 && height==0){
			width=port->getActualWidth();
			height=port->getActualHeight();
		}

		if(stereoOffset!=0.0) // double width for stereo image rendering
			width*=2;

		// if there's no stored texture or we're requesting a different dimension/format, create a new texture
		if(rtt_texture.isNull() || rtt_texture->getWidth()!=width || rtt_texture->getHeight()!=height || rtt_texture->getFormat()!=convert(format)){
			Ogre::TextureManager& tmgr=Ogre::TextureManager::getSingleton();
			
			std::stringstream name;
			name << "RttTex" << std::hex << u64(this) << std::dec;
			
			// remove old viewport if it's associated with the old texture or has a 0 dimensions ie. camera is secondary and not meant to render to the main view
			if(port && (port->getWidth()==0 || port->getHeight()==0 || port->getTarget()==rt)){
				port->getTarget()->removeViewport(port->getZOrder());
				port=NULL;
			}

			// delete the old texture if it exists
			if(!rtt_texture.isNull())
				tmgr.remove(rtt_texture->getName());
		
			// create a new texture
			rtt_texture = tmgr.createManual(name.str().c_str(), scene->resGroupName, Ogre::TEX_TYPE_2D,width,height, 0, convert(format), Ogre::TU_RENDERTARGET);

			// create a viewport to associate the camera with the texture			
			rt = rtt_texture->getBuffer()->getRenderTarget();
			Ogre::Viewport *p=rt->addViewport(camera);
			if(port==NULL){
				port=p;
				setViewport();
			}

			// set port values, most importantly the visibility mask
			p->setVisibilityMask(mask);
			p->setClearEveryFrame(true);
			p->setBackgroundColour(bg);
			p->setOverlaysEnabled(false);
		}

		real aspect=camera->getAspectRatio(); // recall current aspect ratio which can vary from that of the texture
		bool origsetting=scene->getRenderHighQuality(); // recall current high quality render setting
		scene->setRenderHighQuality(true); // force high quality rendering

		if(stereoOffset==0.0){ // monoscopic rendering
			camera->setAspectRatio(real(width)/height);
			rt->update(); // render to the texture in high quality mode
		}
		else{ // stereoscopic rendering
			Ogre::Viewport *p=rt->getViewport(0); // get the texture viewport, this is the same p as above
			Ogre::Quaternion orient=camera->getOrientation();
			vec3 offset=convert(orient*Ogre::Vector3(stereoOffset,0,0));

			vec3 pos=getPosition();
			vec3 look=getLookAt();

			camera->setAspectRatio(real(width*0.5)/height); // since width is doubled, set the aspect ratio using half the actual texture width

			// move camera to the left and render into half the texture
			camera->setOrientation(orient);
			setLookAt(look);
			setPosition(pos-offset);
			p->setDimensions(0,0,0.5,1.0); // set viewport to cover left half of texture
			rt->update();

			// move camera to the right and render into half the texture
			camera->setOrientation(orient);
			setLookAt(look);
			setPosition(pos+offset);
			p->setDimensions(0.5,0,0.5,1.0);  // set viewport to cover right half of texture
			rt->update();

			// reset camera to original position
			camera->setOrientation(orient);
			setLookAt(look);
			setPosition(pos);
		}

		// reset scene and camera config
		scene->setRenderHighQuality(origsetting);
		camera->setAspectRatio(aspect);
	}
	catch(Ogre::Exception &e){
		THROW_RENDEREX(e);
	}
}

OgreBBSetFigure::OgreBBSetFigure(const std::string & name,const std::string & matname,OgreRenderScene *scene,FigureType type) throw(RenderException) :
		node(NULL),scene(scene),matname(matname), name(name),type(type),isInitialized(false),width(1.0),height(1.0)
{
	node=scene->createNode(this);
}

void OgreBBSetFigure::setCameraVisibility(const Camera* cam, bool isVisible)
{
	for(bbsetlist::iterator i=sets.begin();i!=sets.end();++i){
		/*Ogre::Camera *ocam=scene->mgr->getCamera(cam->getName());
		u32 flag=ocam->getViewport()->getVisibilityMask();

		if(isVisible)
			(*i)->addVisibilityFlags(flag);
		else
			(*i)->removeVisibilityFlags(flag);
		*/
		OgreRenderTypes::setCameraVisibility(cam,*i,isVisible,scene);
	}
}

void OgreBBSetFigure::createBBSet()
{
	std::ostringstream out;
	out << name << sets.size();

	Ogre::BillboardSet* bbset=scene->mgr->createBillboardSet(out.str(),SETSIZE);
	bbset->setMaterialName(matname);
	bbset->setDefaultDimensions(width,height);
	bbset->setVisibilityFlags(sets.size()>0 ? sets[0]->getVisibilityFlags() : 1);
	
	switch(type){
	case FT_BB_POINT:
		bbset->setBillboardType(Ogre::BBT_POINT);
		break;
	case FT_BB_FIXED_PAR:
		bbset->setBillboardType(Ogre::BBT_ORIENTED_SELF);
		break;
	case FT_BB_FIXED_PERP:
		bbset->setBillboardType(Ogre::BBT_PERPENDICULAR_SELF);
		break;
	}
	
	node->attachObject(bbset);
	
	sets.push_back(bbset);
}

void OgreBBSetFigure::fillData(const VertexBuffer* vb, const IndexBuffer* ib,bool deferFill,bool doubleSided) throw(RenderException) 
{
	for(bbsetlist::iterator i=sets.begin();i!=sets.end();++i)
		(*i)->clear();
	
	for (sval i = 0; i <vb->numVertices(); i++) {
		if(i==SETSIZE*sets.size())
			createBBSet();
		
		Ogre::BillboardSet* bbset=sets[i/SETSIZE];
		
		vec3 v=vb->getVertex(i);
		
		color col=vb->hasColor() ? vb->getColor(i) : color();
		Ogre::Billboard *b=bbset->createBillboard(convert(v),convert(col));
		
		if(vb->hasNormal()){
			vec3 n=vb->getNormal(i);
			if(n.isZero())
				b->mDirection=Ogre::Vector3::UNIT_Y;
			else
				b->mDirection=convert(n.norm());
		}
	}
}

void OgreBBSetFigure::setVisible(bool isVisible)
{
	if(sets.size()>0){
		if(node->numAttachedObjects()==0)
			for(bbsetlist::iterator i=sets.begin();i!=sets.end();++i)
				node->attachObject(*i);
			
		node->setVisible(isVisible);
	}
}

OgreRibbonFigure::OgreRibbonFigure(const std::string & name,const std::string & matname,OgreRenderScene *scene) throw(RenderException) :
	node(NULL), bbchain(NULL), scene(scene), name(name), matname(matname), orient(0)
{
	node=scene->createNode(this);
	bbchain=scene->mgr->createBillboardChain(name);
	node->attachObject(bbchain);
	scene->mgr->addRenderObjectListener(this);
}

OgreRibbonFigure::~OgreRibbonFigure() 
{
	scene->mgr->removeRenderObjectListener(this);
	scene->mgr->destroyBillboardChain(bbchain);
	scene->destroyNode(node);
}

void OgreRibbonFigure::fillData(const VertexBuffer* vb, const IndexBuffer* ib,bool deferFill,bool doubleSided) throw(RenderException) 
{
	try{
		size_t numverts=vb ? vb->numVertices() : 0;
		size_t numinds=ib ? ib->numIndices() : 0;
		size_t numnodesmax=0;

		for(size_t i=0;i<numinds;i++)
			numnodesmax=_max<size_t>(numnodesmax,ib->indexWidth(i));

		if(numverts==0 || numinds==0 || numnodesmax==0)
			return;

		clearRibbons();
		setNumRibbons(numinds);
		setMaxNodes(numnodesmax);

		for(size_t i=0;i<numinds;i++){
			size_t numnodes=ib->indexWidth(i);
			for(size_t j=0;j<numnodes;j++){
				indexval ind=ib->getIndex(i,j);

				vec3 pos = vb->getVertex(i),norm,uvw;
				color col;
				rotator rot;
				real width=1.0, tex=1.0;
					
				if(vb->hasNormal()){
					norm=vb->getNormal(i);
					if(!norm.isZero())
						rot=rotator(vec3(0,0,1),norm);
				}
		
				if(vb->hasUVWCoord()){
					uvw=vb->getUVWCoord(i);
					width=uvw.y() ? uvw.y() : 1.0;
					tex=uvw.x() ? uvw.x() : 1.0;
				}
			
				if(vb->hasColor())
					col=vb->getColor(i);

				addNode(i,pos,col,width,rot,tex);
			}
		}
	} catch(Ogre::Exception &e){
		THROW_RENDEREX(e);
	}
}

void OgreRibbonFigure::setCameraVisibility(const Camera* cam, bool isVisible)
{
	/*Ogre::Camera *ocam=scene->mgr->getCamera(cam->getName());
	u32 flag=ocam->getViewport()->getVisibilityMask();

	if(isVisible)
		bbchain->addVisibilityFlags(flag);
	else
		bbchain->removeVisibilityFlags(flag);
	*/
	OgreRenderTypes::setCameraVisibility(cam,bbchain,isVisible,scene);
}

std::pair<sval,planevert*> TextureVolumeRenderable::getPlaneIntersects(vec3 planept, vec3 planenorm)
{
	for(int i=0;i<8;i++)
		heights[i]=fig->boundcube[i].planeDist(planept,planenorm);

	sval numpts=calculateHexValueIntersects(0,heights,bbintersects); // determine where the plane intersects the bound box
		
	// fill interpts with the position and uvw coordinates
	for(sval j=0;j<numpts;j++){
		indexval ind1=bbintersects[j].first;
		indexval ind2=bbintersects[j].second;
		real lerpval=bbintersects[j].third;
			
		interpts[j].first=lerp(lerpval,fig->boundcube[ind1],fig->boundcube[ind2]); 
		interpts[j].second=lerp(lerpval,fig->texcube[ind1],fig->texcube[ind2]); 
			
		if(j==0) // choose the first position as the point on the plane to order with
			planept=interpts[j].first;
		else // move the added vertex up to the correct position in the list to maintain clockwise circular ordering
			for(sval jj=j;jj>0 && planept.planeOrder(planenorm,interpts[jj].first,interpts[jj-1].first)>0;jj--)
				bswap(interpts[jj],interpts[jj-1]);
	}

	return std::pair<sval,planevert*>(numpts,interpts);
}

void TextureVolumeRenderable::_updateRenderQueue(Ogre::RenderQueue* queue)
{
	rotator camrot=fig->getRotation(true).inverse()*lastCamRot;
	vec3 figscale=fig->getScale(true).inv();

	vec3 camdir=((vec3(0,0,1)*camrot)*figscale).norm();
					
	float norm[3]; // store the camera direction as a float 3-vector
	(camdir*-1).setBuff(norm);

	Ogre::RGBA ocol; // store the vertex color (white with given alpha) as an Ogre color
	Ogre::RenderSystem* rs=Ogre::Root::getSingleton().getRenderSystem();
	rs->convertColourValue(Ogre::ColourValue(1.0f,1.0f,1.0f,fig->alpha),&ocol);

	sval numplanes=fig->numplanes;
	if(scene!=NULL && !scene->getRenderHighQuality())
		numplanes=_max<sval>(100,numplanes/4);
	
	vec3 center=fig->bbcenter; // bound box center
	real radius=fig->bbradius; // bound box radius
	real radstep=(2.0*radius)/numplanes; // distance between planes
				
	vertices.setN(0);
	indices.setN(0);
	
	// for each plane, determine where it intersects the bound box, sort those points, and store them with uvw coordinates and triangle indices
	for(sval i=0;i<numplanes;i++){
		vec3 planept=center+camdir*(i*radstep-radius); // center of plane

		std::pair<sval,planevert*> result=getPlaneIntersects(planept,camdir); // get the intersection of the given plane with the volume
		sval numpts=result.first;
		sval startind=sval(vertices.n());

		for(sval j=0;j<numpts;j++){ // store vertex information
			OgreBaseRenderable::Vertex v;
			interpts[j].first.setBuff(v.pos);
			interpts[j].second.setBuff(v.tex);
			v.norm[0]=norm[0];
			v.norm[1]=norm[1];
			v.norm[2]=norm[2];
			v.col=ocol;
			vertices.append(v);
		}
				
		// store triangle indices, because the vertices are in a circular order we can easily make a triangle fan
		for(sval j=0;(j+2)<numpts;j++){ // there are 2 fewer indices than there are vertices hence (j+2), use this instead of (numpts-2) in case numpts is 0
			indices.append(startind,0);
			indices(indices.n()-1,1)=startind+j+1;
			indices(indices.n()-1,2)=startind+j+2;
		}
	}
	
	// fill the vertex and index buffers
	if(vertices.n()==0) // if no points fill the buffer with trivial data
		fillDefaultData();
	else{
		createBuffers(vertices.n(),indices.n()*3);
		commitMatrices(&vertices,&indices);
	}
	
	OgreBaseRenderable::_updateRenderQueue(queue);
}

void TextureVolumeRenderable::_notifyCurrentCamera(Ogre::Camera* cam)
{
	OgreBaseRenderable::_notifyCurrentCamera(cam);
	lastCamRot=convert(cam->getDerivedOrientation());
}

vec3* calculateTriNorms(vec3* nodes, sval numnodes, indexval* inds, sval numinds)
{
	vec3* norms=new vec3[numnodes];
	memset(norms,0,sizeof(vec3)*numnodes);

	for(sval i=0;i<numinds;i++){
		indexval a=inds[i*3],b=inds[i*3+1],c=inds[i*3+2];
		vec3 norm=nodes[a].planeNorm(nodes[b],nodes[c]);
		norms[a]=norms[a]+norm;
		norms[b]=norms[b]+norm;
		norms[c]=norms[c]+norm;
	}

	for(sval n=0;n<numnodes;n++)
		norms[n]=norms[n].norm();

	return norms;
}

void OgreGlyphFigure::fillDefaultGlyphs(glyphmap &map)
{
	static vec3 cubenodes[]={
		vec3(-0.5,0.5,0.5), vec3(0.5,0.5,0.5), vec3(-0.5,-0.5,0.5), vec3(0.5,-0.5,0.5), vec3(-0.5,-0.5,-0.5), vec3(0.5,-0.5,-0.5), 
		vec3(-0.5,0.5,-0.5), vec3(0.5,0.5,-0.5), vec3(-0.5,-0.5,0.5), vec3(0.5,-0.5,0.5), vec3(-0.5,-0.5,-0.5), vec3(0.5,-0.5,-0.5), 
		vec3(-0.5,0.5,-0.5), vec3(0.5,0.5,-0.5), vec3(-0.5,0.5,0.5), vec3(0.5,0.5,0.5), vec3(0.5,0.5,0.5), vec3(0.5,0.5,-0.5), 
		vec3(0.5,-0.5,0.5), vec3(0.5,-0.5,-0.5), vec3(-0.5,0.5,-0.5), vec3(-0.5,0.5,0.5), vec3(-0.5,-0.5,-0.5), vec3(-0.5,-0.5,0.5)
	};
	static indexval cubeinds[][3]={
		{0, 2, 1}, {1, 2, 3}, {4, 6, 5}, {5, 6, 7}, {8, 10, 9}, {9, 10, 11}, {12, 14, 13}, {13, 14, 15}, {16, 18, 17}, {17, 18, 19}, {20, 22, 21}, {21, 22, 23}
	};

	static vec3* cubenorms=calculateTriNorms(cubenodes,24,(indexval*)cubeinds,12);

	static vec3 spherenodes[]={
		vec3(0,0,1), vec3(0,-0.894427191,0.4472135955), vec3(0,0.894427191,-0.4472135955), vec3(0,0,-1), 
		vec3(0.5257311121,0.7236067977,0.4472135955), vec3(-0.5257311121,0.7236067977,0.4472135955), vec3(0.5257311121,-0.7236067977,-0.4472135955), 
		vec3(-0.5257311121,-0.7236067977,-0.4472135955), vec3(0.8506508084,-0.2763932023,0.4472135955), vec3(-0.8506508084,-0.2763932023,0.4472135955), 
		vec3(0.8506508084,0.2763932023,-0.4472135955), vec3(-0.8506508084,0.2763932023,-0.4472135955), vec3(0,-0.5257311121,0.8506508084), vec3(0.5,-0.1624598481,0.8506508084), 
		vec3(0.5,-0.6881909602,0.5257311121), vec3(-0.5,-0.1624598481,0.8506508084), vec3(-0.5,-0.6881909602,0.5257311121), vec3(0.3090169944,0.4253254042,0.8506508084), 
		vec3(0.8090169944,0.2628655561,0.5257311121), vec3(-0.3090169944,0.4253254042,0.8506508084), vec3(0,0.8506508084,0.5257311121), 
		vec3(-0.8090169944,0.2628655561,0.5257311121), vec3(0,0.5257311121,-0.8506508084), vec3(-0.5,0.6881909602,-0.5257311121), vec3(-0.5,0.1624598481,-0.8506508084), 
		vec3(-0.3090169944,0.9510565163,0), vec3(-0.8090169944,0.5877852523,0), vec3(0.3090169944,0.9510565163,0), 
		vec3(0.5,0.6881909602,-0.5257311121), vec3(0.8090169944,0.5877852523,0), vec3(0.5,0.1624598481,-0.8506508084), 
		vec3(-0.3090169944,-0.9510565163,0), vec3(-0.8090169944,-0.5877852523,0), vec3(0.3090169944,-0.9510565163,0), 
		vec3(0,-0.8506508084,-0.5257311121), vec3(0.8090169944,-0.5877852523,0), vec3(0.3090169944,-0.4253254042,-0.8506508084), 
		vec3(0.8090169944,-0.2628655561,-0.5257311121), vec3(-0.3090169944,-0.4253254042,-0.8506508084), vec3(-0.8090169944,-0.2628655561,-0.5257311121), 
		vec3(1,0,0), vec3(-1,0,0)
	};

	static indexval sphereinds[][3]={
		{0, 12, 13}, {12, 1, 14}, {13, 14, 8}, {12, 14, 13}, {0, 15, 12}, {15, 9, 16}, {12, 16, 1}, {15, 16, 12}, {0, 13, 17}, {13, 8, 18}, {17, 18, 4}, {13, 18, 17}, {0, 17, 19}, 
		{17, 4, 20}, {19, 20, 5}, {17, 20, 19}, {0, 19, 15}, {19, 5, 21}, {15, 21, 9}, {19, 21, 15}, {2, 22, 23}, {22, 3, 24}, {23, 24, 11}, {22, 24, 23}, {2, 23, 25}, {23, 11, 26}, 
		{25, 26, 5}, {23, 26, 25}, {2, 25, 27}, {25, 5, 20}, {27, 20, 4}, {25, 20, 27}, {2, 27, 28}, {27, 4, 29}, {28, 29, 10}, {27, 29, 28}, {2, 28, 22}, {28, 10, 30}, {22, 30, 3}, 
		{28, 30, 22}, {1, 16, 31}, {16, 9, 32}, {31, 32, 7}, {16, 32, 31}, {1, 31, 33}, {31, 7, 34}, {33, 34, 6}, {31, 34, 33}, {1, 33, 14}, {33, 6, 35}, {14, 35, 8}, {33, 35, 14}, 
		{3, 30, 36}, {30, 10, 37}, {36, 37, 6}, {30, 37, 36}, {3, 36, 38}, {36, 6, 34}, {38, 34, 7}, {36, 34, 38}, {3, 38, 24}, {38, 7, 39}, {24, 39, 11}, {38, 39, 24}, {4, 18, 29}, 
		{18, 8, 40}, {29, 40, 10}, {18, 40, 29}, {5, 26, 21}, {26, 11, 41}, {21, 41, 9}, {26, 41, 21}, {6, 37, 35}, {37, 10, 40}, {35, 40, 8}, {37, 40, 35}, {7, 32, 39}, {32, 9, 41}, 
		{39, 41, 11}, {32, 41, 39}
	};

	static vec3* spherenorms=calculateTriNorms(spherenodes,42,(indexval*)sphereinds,80);

	static vec3 arrownodes[]={
		vec3(0,0,-1), 
		vec3(0.375,0,-1), vec3(0.1875,-0.3247595264,-1), vec3(-0.1875,-0.3247595264,-1), vec3(-0.375,0,-1), vec3(-0.1875,0.3247595264,-1), vec3(0.1875,0.3247595264,-1), 
		vec3(0.375,0,-1), vec3(0.1875,-0.3247595264,-1), vec3(-0.1875,-0.3247595264,-1), vec3(-0.375,0,-1), vec3(-0.1875,0.3247595264,-1), vec3(0.1875,0.3247595264,-1), 
		vec3(0.375,0,0), vec3(0.1875,-0.3247595264,0), vec3(-0.1875,-0.3247595264,0), vec3(-0.375,0,0), vec3(-0.1875,0.3247595264,0), vec3(0.1875,0.3247595264,0), 
		vec3(1,0,0), vec3(0.5,-0.8660254038,0), vec3(-0.5,-0.8660254038,0), vec3(-1,0,0), vec3(-0.5,0.8660254038,0), vec3(0.5,0.8660254038,0), 
		vec3(1,0,0), vec3(0.5,-0.8660254038,0), vec3(-0.5,-0.8660254038,0), vec3(-1,0,0), vec3(-0.5,0.8660254038,0), vec3(0.5,0.8660254038,0), 
		vec3(0,0,1)
	};

	static indexval arrowinds[][3]={
		{0, 1, 2}, {0, 2, 3}, {0, 3, 4}, {0, 4, 5}, {0, 5, 6}, {0, 6, 1}, {7, 13, 8}, {8, 13, 14}, {8, 14, 9}, {9, 14, 15}, {9, 15, 10}, {10, 15, 16}, {10, 16, 11}, {11, 16, 17}, 
		{11, 17, 12}, {12, 17, 18}, {12, 18, 7}, {7, 18, 13}, {13, 19, 14}, {14, 19, 20}, {14, 20, 15}, {15, 20, 21}, {15, 21, 16}, {16, 21, 22}, {16, 22, 17}, {17, 22, 23}, 
		{17, 23, 18}, {18, 23, 24}, {18, 24, 13}, {13, 24, 19}, {31, 26, 25}, {31, 27, 26}, {31, 28, 27}, {31, 29, 28}, {31, 30, 29}, {31, 25, 30}
	};

	static vec3* arrownorms=calculateTriNorms(arrownodes,32,(indexval*)arrowinds,36);

	map["cube"]=glyphmesh(new Vec3Matrix("cubenodes","",(vec3*)cubenodes,24,1),new Vec3Matrix("cubenorms","",(vec3*)cubenorms,24,1),new IndexMatrix("cubeinds","",(indexval*)cubeinds,12,3));
	map["sphere"]=glyphmesh(new Vec3Matrix("spherenodes","",(vec3*)spherenodes,42,1),new Vec3Matrix("spherenorms","",(vec3*)spherenorms,42,1),new IndexMatrix("sphereinds","",(indexval*)sphereinds,80,3));
	map["arrow"]=glyphmesh(new Vec3Matrix("arrownodes","",(vec3*)arrownodes,32,1),new Vec3Matrix("arrownorms","",(vec3*)arrownorms,32,1),new IndexMatrix("arrowinds","",(indexval*)arrowinds,36,3));
}

OgreGlyphFigure::OgreGlyphFigure(const std::string& name,const std::string & matname,OgreRenderScene *scene) throw(RenderException)
	: OgreBaseFigure(new OgreBaseRenderable(name,matname,convert(FT_TRILIST),scene->mgr),scene->createNode(this),scene),glyphscale(1),glyphname("sphere")
{
	OgreGlyphFigure::fillDefaultGlyphs(glyphs);
}

void OgreGlyphFigure::fillData(const VertexBuffer* vb, const IndexBuffer* ib,bool deferFill,bool doubleSided) throw(RenderException)
{
	Ogre::RenderSystem* rs=Ogre::Root::getSingleton().getRenderSystem();

	glyphmap::const_iterator i=glyphs.find(glyphname);

	critical(obj->getMutex()){
		if(vb->numVertices()==0 || i==glyphs.end()){
			obj->fillDefaultData();
			node->needUpdate();
			return;
		}

		const glyphmesh gmesh=(*i).second;
		const Vec3Matrix* gverts=gmesh.first;
		const Vec3Matrix* gnorms=gmesh.second;
		const IndexMatrix* ginds=gmesh.third;

		sval numverts=gverts->n(), numinds=ginds->n();

		obj->createBuffers(vb->numVertices()*numverts,vb->numVertices()*numinds*3);

		vec3 minv=vb->getVertex(0), maxv=vb->getVertex(0);

		OgreBaseRenderable::Vertex *vbuf=obj->getLocalVertBuff();
		indexval *ibuf=obj->getLocalIndBuff();

		for (sval g = 0; g < vb->numVertices(); g++) {
			vec3 pos = vb->getVertex(g),dir(0,0,1),scale=glyphscale;
			color col;

			if(vb->hasNormal())
				dir=vb->getNormal(g);
			
			if(vb->hasUVWCoord())
				scale=scale*vb->getUVWCoord(g);

			if(vb->hasColor())
				col=vb->getColor(g);
				
			rotator rot(vec3(0,0,1),dir);
			transform trans(pos,scale,rot);

			sval vstart=numverts*g;
			sval istart=numinds*3*g;

			for(sval v=0;v<numverts;v++){
				vec3 vert=gverts->at(v)*trans;
				vec3 norm=gnorms->at(v)*rot;

				minv.setMinVals(vert);
				maxv.setMaxVals(vert);

				vert.setBuff(vbuf[v+vstart].pos);
				norm.setBuff(vbuf[v+vstart].norm);
				vec3().setBuff(vbuf[v+vstart].tex);

				if(rs){
					Ogre::ColourValue c = convert(col);
					rs->convertColourValue(c,&vbuf[v+vstart].col);
				}
				else
					vbuf[v+vstart].col=col.toRGBA();
			}

			for(sval i=0;i<numinds;i++){
				ibuf[i*3+istart]=ginds->at(i,0)+vstart;
				ibuf[i*3+istart+1]=ginds->at(i,1)+vstart;
				ibuf[i*3+istart+2]=ginds->at(i,2)+vstart;
			}
		}

	
		obj->commitBuffers();
		obj->setBoundingBox(minv,maxv);
		obj->deleteLocalIndBuff();
		obj->deleteLocalVertBuff();
		node->needUpdate();
	}
}

OgreTextFigure::OgreTextFigure(const std::string& name,OgreRenderScene *scene) throw(RenderException)
	: OgreBaseFigure(new TextRenderable(name,scene->mgr),scene->createNode(this),scene)
{}

void TextRenderable::_notifyCurrentCamera(Ogre::Camera* cam)
{
	OgreBaseRenderable::_notifyCurrentCamera(cam);
	mParentNode->setOrientation(cam->getDerivedOrientation()); // rotate to face camera
}

void TextRenderable::_updateRenderQueue(Ogre::RenderQueue* queue)
{
	if(isVisible()){
		if (updateGeom)
			updateGeometry();
		if (updateCols)
			updateColors();
	
		if (mRenderQueuePrioritySet)
			queue->addRenderable(this, mRenderQueueID, mRenderQueuePriority);
		else if(mRenderQueueIDSet)
			queue->addRenderable(this, mRenderQueueID);
		else
			queue->addRenderable(this);
	}
}

void TextRenderable::setFont(const std::string& fontname) throw(RenderException)
{
	Ogre::FontPtr newfontobj = Ogre::FontManager::getSingletonPtr()->getByName(fontname);
	if(newfontobj.isNull())
		throw RenderException("Cannot find font "+fontname,__FILE__,__LINE__);
	
	this->fontname=fontname;
	updateCols=true;
	updateGeom=true;
}

void TextRenderable::updateColors()
{
	Ogre::RGBA col;
	Ogre::RenderSystem* rs=Ogre::Root::getSingleton().getRenderSystem();
	rs->convertColourValue(convert(this->col), &col);
	
	Ogre::RGBA *buf = static_cast<Ogre::RGBA*>(colBuf->lock(Ogre::HardwareBuffer::HBL_DISCARD));
	
	for (size_t i = 0; i < vertexData->vertexCount; i++)
		buf[i] = col;
	
	colBuf->unlock();
	updateCols = false;
}

void TextRenderable::updateGeometry()
{
	std::string name=getName();
	std::string internalmatname=name+"TextMat";
	
	if(!fontobj || fontname!=fontobj->getName() || mat.isNull()){
		Ogre::Font* newfontobj = (Ogre::Font *)Ogre::FontManager::getSingleton().getByName(fontname).getPointer();
		
		if (!newfontobj)
			throw Ogre::Exception(Ogre::Exception::ERR_ITEM_NOT_FOUND, "Could not find font " + fontname, "TextRenderable::updateGeometry");
		
		fontobj=newfontobj;
		fontobj->load();
		
		if(!mat.isNull() && mat->getName()==internalmatname){
			Ogre::MaterialManager::getSingletonPtr()->remove(internalmatname);
			mat.setNull();
		}
		
		mat = fontobj->getMaterial()->clone(internalmatname);
		if(!mat->isLoaded())
			mat->load();
		
		mat->setLightingEnabled(false);
		setOverlay(isOverlay);
	}
	
	std::string::iterator iend = text.end();
	size_t pos=0;
	int numlines=1;
	vec3 min=vec3::posInfinity(), max=vec3::negInfinity();
	float left=0,top=0;
	float swidth=spaceWidth ? spaceWidth : fontobj->getGlyphAspectRatio('A') * textHeight*0.5; // get the defined space width or derive from 'A'
	bool startline=true;
 
	destroyBuffers();
	vertexData = OGRE_NEW Ogre::VertexData();
	vertexData->vertexStart = 0;
	vertexData->vertexCount = 0; 
	
	// determine the vertex count and line where a quad of 6 vertices is made for every non-whitespace character
	for (std::string::iterator i = text.begin(); i != iend; i++){
		if(!std::isspace(*i))
			vertexData->vertexCount+=6; // 6 vertices for 1 quad per non-whitespace character
		
		if((*i)=='\n')
			numlines+=1;
	}
 
	Ogre::HardwareBufferManager& hbm=Ogre::HardwareBufferManager::getSingleton();
	Ogre::VertexDeclaration *decl = vertexData->vertexDeclaration;
	Ogre::VertexBufferBinding *bind = vertexData->vertexBufferBinding;
	
	// define a vertex type of a float3 position element followed by a float2 texture coord element (ie. (x,y,z,u,v))
	decl->addElement(POS_TEX_BINDING, 0, Ogre::VET_FLOAT3, Ogre::VES_POSITION);
	decl->addElement(POS_TEX_BINDING, Ogre::VertexElement::getTypeSize(Ogre::VET_FLOAT3), Ogre::VET_FLOAT2, Ogre::VES_TEXTURE_COORDINATES, 0);
	decl->addElement(COLOUR_BINDING, 0, Ogre::VET_COLOUR, Ogre::VES_DIFFUSE);
 
	vertBuf = hbm.createVertexBuffer(decl->getVertexSize(POS_TEX_BINDING), vertexData->vertexCount, Ogre::HardwareBuffer::HBU_DYNAMIC_WRITE_ONLY);
	colBuf = hbm.createVertexBuffer(decl->getVertexSize(COLOUR_BINDING), vertexData->vertexCount, Ogre::HardwareBuffer::HBU_DYNAMIC_WRITE_ONLY);
	
	bind->setBinding(POS_TEX_BINDING, vertBuf);
	bind->setBinding(COLOUR_BINDING, colBuf);

	TextVertex *buf = static_cast<TextVertex*>(vertBuf->lock(Ogre::HardwareBuffer::HBL_DISCARD));
	
	if(valign==V_BOTTOM)
		top += textHeight*numlines;
	else if(valign==V_CENTER)
		top += 0.5*textHeight*numlines;
	
	for (std::string::iterator i = text.begin(); i != iend; i++){
		unsigned int c=*i;
		
		if(startline){ // new line so move the line start position (\r, \v, \f treated as spaces)
			startline=false;
			float wline=0;
			
			for (std::string::iterator j = i; j != iend && *j!='\n'; j++) {
				if(std::isspace(*j))
					wline+=swidth;
				else
					wline+=fontobj->getGlyphAspectRatio(*j)*textHeight;
			}
			
			// move left to adjust for horizontal alignment based on the computed line width 
			if(halign==H_CENTER)
				left=-wline*0.5;
			else if(halign==H_RIGHT)
				left=-wline;
			else
				left=0;
		}
		
		if(c=='\n'){
			startline=true;
			top-=textHeight; // move down to next line
		}
		else if (std::isspace(c)) // space (or some other control character other than \n), just move to the left by the space width
			left+=swidth;
		else{
			Ogre::Font::UVRect uv = fontobj->getGlyphTexCoords(c);
			float cw = fontobj->getGlyphAspectRatio(c) * textHeight;
			float ch=-textHeight;
			
			buf[pos  ].set(left,   top,   uv.left, uv.top,   min,max); // top left
			buf[pos+1].set(left,   top+ch,uv.left, uv.bottom,min,max); // bottom left
			buf[pos+2].set(left+cw,top,   uv.right,uv.top,   min,max); // top right
			buf[pos+3].set(left+cw,top,   uv.right,uv.top,   min,max); // top right
			buf[pos+4].set(left,   top+ch,uv.left, uv.bottom,min,max); // bottom left
			buf[pos+5].set(left+cw,top+ch,uv.right,uv.bottom,min,max); // bottom right
			
			left += cw;
			pos+=6; // advance to next quad
		}
	}
	
	vertBuf->unlock();
 
	setBoundingBox(min,max);
	updateGeom = false;
	updateCols = true;
	//mParentNode->needUpdate();
}

void OgreTexture::fillBlack()
{
	Ogre::HardwarePixelBufferSharedPtr buff= ptr->getBuffer();
	buff->lock(Ogre::HardwareBuffer::HBL_WRITE_ONLY);
	memset(buff->getCurrentLock().data,0,buff->getSizeInBytes());
	buff->unlock();
}

void OgreTexture::fillColor(color col)
{
	sval w=getWidth();
	sval h=getHeight();
	sval d=getDepth();

	Ogre::HardwarePixelBufferSharedPtr buff= ptr->getBuffer();
	void* data=buff->lock(Ogre::HardwareBuffer::HBL_WRITE_ONLY);
	Ogre::PixelBox pb(w,h,d,ptr->getFormat(),data);

	Ogre::ColourValue cv=convert(col);
	for(sval z=0;z<d;z++)
		for(sval y=0;y<h;y++)
			for(sval x=0;x<w;x++)
				pb.setColourAt(cv,x,y,z);

	buff->unlock();
}

void OgreTexture::fillColor(const ColorMatrix *mat,indexval depth)
{
	sval w=getWidth();
	sval h=getHeight();
	sval d=getDepth();

	Ogre::HardwarePixelBufferSharedPtr buff= ptr->getBuffer();
	void* data=buff->lock(Ogre::HardwareBuffer::HBL_WRITE_ONLY);
	Ogre::PixelBox pb(w,h,d,ptr->getFormat(),data);

	for(sval y=0;y<h;y++)
		for(sval x=0;x<w;x++)
			pb.setColourAt(convert(mat->at(y,x)),x,y,depth);

	buff->unlock();
}

void OgreTexture::fillColor(const RealMatrix *mat,indexval depth,real minval,real maxval, const Material* colormat,const RealMatrix *alphamat,bool mulAlpha)
{
	sval w=getWidth();
	sval h=getHeight();
	sval d=getDepth();

	Ogre::HardwarePixelBufferSharedPtr buff= ptr->getBuffer();
	void* data=buff->lock(Ogre::HardwareBuffer::HBL_WRITE_ONLY);
	Ogre::PixelBox pb(w,h,d,ptr->getFormat(),data);
	Ogre::ColourValue col;

	for(sval y=0;y<h;y++)
		for(sval x=0;x<w;x++){
			real val=lerpXi(mat->at(y,x),minval,maxval);
			
			if(colormat!=NULL){
				color c=colormat->interpolateColor(val);
				c.setBuff(&col.r);
			}
			else{
				col.r=col.g=col.b=val;
				col.a=1.0;
			}

			if(alphamat!=NULL)
				col.a=alphamat->at(y,x);

			if(mulAlpha)
				col.a*=val; // set alpha to the commonly desired value

			pb.setColourAt(col,x,y,depth);
		}

	buff->unlock();
}

OgreRenderAdapter::OgreRenderAdapter(Config *config) throw(RenderException) : mgr(NULL), win(NULL), config(config), scene(NULL) 
{
	try{
		Ogre::LogManager *lm = new Ogre::LogManager(); // this instantiates the global default logger
		
		std::string logfile=config->get(platformID,"logfile");
		std::string vsync=config->get(platformID,"vsync"); // might not be meaningful outside of fullscreen rendering
		
		// if there's a log file specified in `config', send the log there, otherwise send it nowhere
		if(logfile.size()>0)
			lm->createLog(logfile, true, false, false); // don't log to screen
		else
			lm->createLog("Ogre", true, false, true); // don't log at all
	
		root = new Ogre::Root("","","");
	
		// by default choose OpenGL, there's no option outside of Windows
		std::string rendersys="RenderSystem_GL";
		std::string rendersysname="OpenGL Rendering Subsystem";
		
		// windows has the option of choosing D3D9/10/11 if specified in `config'
#ifdef WIN32
		std::string configsys=config->get(platformID,"rendersystem");
		if(configsys=="D3D9"){
			rendersys="RenderSystem_Direct3D9";
			rendersysname="Direct3D9 Rendering Subsystem";
		}
		else if(configsys=="D3D10"){
			rendersys="RenderSystem_Direct3D10";
			rendersysname="Direct3D10 Rendering Subsystem";
		}
		else if(configsys=="D3D11"){
			rendersys="RenderSystem_Direct3D11";
			rendersysname="Direct3D11 Rendering Subsystem";
		}
#endif
	
#ifdef _DEBUG
		rendersys+="_d";
#endif
	
		root->loadPlugin(rendersys);
		Ogre::RenderSystem* rs = root->getRenderSystemByName(rendersysname);
	
		std::string plugins=config->get(platformID,"plugins");
		char *pbuf=new char[plugins.size()+1];
		strcpy(pbuf,plugins.c_str());
		char* s=strtok(pbuf,", ");
	
		// load plugins specified in `config', appending _d to their names if this is a debug build
		while(s!=NULL){
			std::string pluginfile=s;
#ifdef _DEBUG
			pluginfile+="_d";
#endif
			root->loadPlugin(pluginfile.c_str());
			s=strtok(NULL," ");
		}
	
		delete pbuf;
	
		// fill in the render system config values

		if(rendersys=="RenderSystem_GL"){
			//rs->setConfigOption("Colour Depth","32");
			rs->setConfigOption("Video Mode", "800 x 600");
		}
		else
			rs->setConfigOption("Video Mode", "800 x 600 @ 32-bit"); // D3D wants this (?)
	
		rs->setConfigOption("Full Screen", "No");
		rs->setConfigOption("VSync", vsync=="true" ? "Yes" : "No");
		
		if(rendersys=="RenderSystem_GL" && config->hasValue(platformID,"rtt_preferred_mode"))
			rs->setConfigOption("RTT Preferred Mode",config->get(platformID,"rtt_preferred_mode")); // FBO, PBuffer, Copy
	
		// print out available render systems to the log
		lm->logMessage("Available Render Systems:");
		const Ogre::RenderSystemList &rsl=root->getAvailableRenderers();
		for(Ogre::RenderSystemList::const_iterator i=rsl.begin();i!=rsl.end();i++){
			std::ostringstream os;
			os << "| "<< (*i)->getName();
			lm->logMessage(os.str());
		}
	
		// print out loaded plugins to the log
		lm->logMessage("Loaded Plugins:");
		const Ogre::Root::PluginInstanceList &pil= root->getInstalledPlugins();
		for(Ogre::Root::PluginInstanceList::const_iterator i=pil.begin();i!=pil.end();i++){
			std::ostringstream os;
			os << "| "<< (*i)->getName();
			lm->logMessage(os.str());
		}
	
		// print out available config options and their possible values to the log
		lm->logMessage("Config Options:");	
		Ogre::ConfigOptionMap &opts=rs->getConfigOptions();
		for(Ogre::ConfigOptionMap::iterator i=opts.begin();i!=opts.end();i++){
			std::ostringstream os;
			os << "| " << (*i).first << " = " << (*i).second.currentValue << ", Possible Values = ";
			
			Ogre::StringVector possibles=(*i).second.possibleValues;
			for(Ogre::StringVector::iterator j=possibles.begin();j!=possibles.end();++j)
				os << "\"" << (*j) << "\" ";
			
			lm->logMessage(os.str());
		}
	
		root->setRenderSystem(rs);
		root->saveConfig();
		root->initialise(false);
		
		overlay=OGRE_NEW Ogre::OverlaySystem(); // initialize the overlay system so that the font manager gets created
		
		Ogre::ResourceManager::ResourceMapIterator fonts=Ogre::FontManager::getSingletonPtr()->getResourceIterator();
		lm->logMessage("Loaded Fonts:");
		for(Ogre::ResourceManager::ResourceMapIterator::const_iterator i=fonts.begin();i!=fonts.end();i++)
			lm->logMessage(std::string("|")+((*i).second.isNull() ? "Null" : (*i).second->getName()));
		
	}
	catch(Ogre::Exception &e){
		THROW_RENDEREX(e);
	}
}

OgreRenderAdapter::~OgreRenderAdapter()
{
	root->shutdown();
	delete root;
}

u64 OgreRenderAdapter::createWindow(int width, int height) throw(RenderTypes::RenderException)
{
	try{	
		const char* paramNames[]={"vsync","border","parentWindowHandle","externalWindowHandle","macAPI","macAPICocoaUseNSView"};
		sval numParamNames=6;
		Ogre::NameValuePairList params;
		u64 ogreWinId = 0;
		
#ifdef __APPLE__
		params["macAPI"] = "cocoa";
		params["macAPICocoaUseNSView"] = "true";
#endif
		
		for(sval i=0;i<numParamNames;i++){
			if(config->hasValue(RenderParamGroup,paramNames[i]))
				params[paramNames[i]]=config->get(RenderParamGroup,paramNames[i]);
		}
	
		win = root->createRenderWindow("Ogre_RenderWindow", width, height, false, &params);
		win->setActive(true);
		win->setVisible(true);
	
		mgr = root->createSceneManager(Ogre::ST_INTERIOR);
		
		// the winID number is meaningful only for OSX but even then it's not used on the Python side
#ifndef __APPLE__
		win->getCustomAttribute("WINDOW", &ogreWinId);
#endif
	
		return ogreWinId; 
	}
	catch(Ogre::Exception &e){
		THROW_RENDEREX(e);
	}
}

void OgreRenderAdapter::paint()
{
	if(!root->_fireFrameStarted())
		return;
	
	win->update();

	root->_fireFrameRenderingQueued();
	root->_fireFrameEnded();

	scene->setRenderHighQuality(false);
}

void OgreRenderAdapter::resize(int x, int y,int width, int height)
{
	if(width>0 && height>0){
		win->reposition(x,y);
		win->resize(width,height);
	}
	win->windowMovedOrResized();
}

RenderScene* OgreRenderAdapter::getRenderScene() 
{
	if(scene==NULL)
		scene= new OgreRenderScene(this);

	return scene;
}

} // namespace OgreRenderTypes


