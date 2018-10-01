
import eidolon
from eidolon import (
        Qt, Handle, Handle3D, vec3, rotator,color, transform, MeshSceneObject, PyVertexBuffer, PyIndexBuffer, FT_TRILIST,
        ReprType, halfpi, generatePlane, generateSphere, generateTriNormals, setmethod,isMainThread
        )

import numpy as np
from scipy.spatial import cKDTree

class NodeSelectHandle(Handle3D):
    sphereNodes=None
    sphereInds=None
    sphereNorms=None
    sphereScale=0.25
    
    def __init__(self,positionOffset,kdtree,value,selectCallback=lambda h,i,r:None,col=color(1,0,0,1)):
        Handle3D.__init__(self)
        self.position=vec3()
        self.positionOffset=positionOffset
        self.kdtree=kdtree
        self.value=value
        self.selectCallback=selectCallback
        self.col=col
        self.lastIntersect=None

        if NodeSelectHandle.sphereNodes is None:
            NodeSelectHandle.sphereNodes,NodeSelectHandle.sphereInds=generateSphere(2)
            NodeSelectHandle.sphereNorms=generateTriNormals(NodeSelectHandle.sphereNodes,NodeSelectHandle.sphereInds)
        
    def isSelected(self):
        return self.lastIntersect!=None
   
    def checkSelected(self,ray):
        assert isinstance(ray,eidolon.Ray)
        self.lastIntersect=None
        
        if self.isVisible():
            trans=transform(self.position+self.positionOffset,self.figscale*NodeSelectHandle.sphereScale)
            
            for i,tri in enumerate(NodeSelectHandle.sphereInds):
                tnodes=[trans*NodeSelectHandle.sphereNodes[t] for t in tri]
                result=ray.intersectsTri(*tnodes)
                if len(result)>0:
                    self.lastIntersect=(i,result,ray)
                    return True

        return False
    
    def addToScene(self,mgr,scene):
        assert isMainThread()

        figname='NodeSelectHandle%r'%(self.value,)
        mat=Handle._defaultMaterial(mgr)
        matname=mat.getName()
        
        nodes=[n*NodeSelectHandle.sphereScale for n in NodeSelectHandle.sphereNodes]
        inds=NodeSelectHandle.sphereInds
        norms=NodeSelectHandle.sphereNorms
        
        vbuf=PyVertexBuffer(nodes,norms,[self.col]*len(nodes))
        ibuf=PyIndexBuffer(inds)

        fig=scene.createFigure(figname,matname,FT_TRILIST)
        fig.fillData(vbuf,ibuf)
        fig.setOverlay(True)
        self.figs.append(fig)
        self.setPosition(self.position)
        
    def getAbsolutePosition(self):
        return self.position+self.positionOffset
    
    def setPosition(self,pos):
        self.position=pos
        self.figs[0].setPosition(pos+self.positionOffset)
        
    def mouseDrag(self,e,dragvec):
        if self.buttons==Qt.LeftButton: # translate relative to camera
            campos=self.pressedCamera.getPosition()
            pos=self.getAbsolutePosition()
            r=self.getCameraRay()
            dragpos=r.getPosition(campos.distTo(pos))
            radius=dragpos.distTo(pos)
            
            # find nodes within radius of this handle
            radnodes=self.kdtree.query_ball_point(tuple(self.positionOffset),radius)
            
            eidolon.printFlush(radnodes)
            
    
nodes,_,_=generatePlane(4)

r=rotator(vec3.X(),halfpi)
nodes=[r*n for n in nodes]

obj=MeshSceneObject('nodes',eidolon.PyDataSet('ds',nodes,[],[]))
mgr.addSceneObject(obj)

rep=obj.createRepr(ReprType._glyph,0,externalOnly=False,drawInternal=True,glyphname='sphere',glyphscale=(0.1,0.1,0.1))
mgr.addSceneObjectRepr(rep)

mgr.setCameraSeeAll()


tree=cKDTree(np.asarray(list(map(tuple,nodes))))

@setmethod(rep)
def createHandles():
    h= rep.__old__createHandles()
    
    try:
        ind=15
        h.append(NodeSelectHandle(nodes[ind],tree,(ind,nodes)))
    except Exception as e:
        print(e)
    return h

mgr.showHandle(rep,True)

