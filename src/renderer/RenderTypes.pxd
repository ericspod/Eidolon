# Eidolon Biomedical Framework
# Copyright (C) 2016-7 Eric Kerfoot, King's College London, all rights reserved
# 
# This file is part of Eidolon.
#
# Eidolon is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Eidolon is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program (LICENSE.txt).  If not, see <http://www.gnu.org/licenses/>


'''
This is the Cython C++ interface for RenderTypes.h.
'''

from libcpp.string cimport string
from libcpp.vector cimport vector
from libcpp.pair cimport pair


cdef extern from "RenderTypes.h" namespace "RenderTypes" nogil:
    ctypedef unsigned char u8
    ctypedef long i32
    ctypedef long long i64
    ctypedef unsigned long u32
    ctypedef unsigned long long u64

    ctypedef u64 size_t

    ctypedef double real
    ctypedef u32 sval
    ctypedef u32 rgba
    ctypedef u32 indexval


    cdef cppclass triple[F,S,T]:
        F first
        S second
        T third
        triple()
        triple(const triple[F,S,T]& t)
        triple(const F& f,const S& s,const T& t)


    cdef cppclass quadruple[F,S,T,U]:
        F first
        S second
        T third
        U fourth
        quadruple()
        quadruple(const quadruple[F,S,T,U] &t)
        quadruple(const F& f,const S& s,const T& t, const U& u)


    ctypedef pair[real,real] realpair
    ctypedef pair[indexval,indexval] indexpair
    ctypedef triple[real,real,real] realtriple
    ctypedef pair[indexval,realtriple] indextriple
    ctypedef triple[sval,sval,real] intersect

    cdef char* platformID
    cdef char* RenderParamGroup

    cdef enum FigureType:
        FT_LINELIST      =  0
        FT_POINTLIST     =  1
        FT_TRILIST       =  2
        FT_TRISTRIP      =  3
        FT_BB_POINT      =  4
        FT_BB_FIXED_PAR  =  5
        FT_BB_FIXED_PERP =  6
        FT_GLYPH         =  7
        FT_RIBBON        =  8
        FT_TEXVOLUME     =  9
        FT_TEXT          = 10


    cdef enum BlendMode:
        BM_ALPHA
        BM_COLOR
        BM_ADD
        BM_MOD
        BM_REPLACE


    cdef enum TextureFormat:
        TF_RGB24
        TF_RGBA32
        TF_ARGB32
        TF_LUM8
        TF_LUM16
        TF_ALPHA8
        TF_ALPHALUM8
        TF_UNKNOWN


    cdef enum ProgramType:
        PT_VERTEX   = 0
        PT_FRAGMENT = 1
        PT_GEOMETRY = 2
        
    cdef enum HAlignType:
        H_LEFT
        H_RIGHT
        H_CENTER
    
    cdef enum VAlignType:
        V_TOP
        V_BOTTOM
        V_CENTER


    T _min[T](const T& a, const T& b)
    T _max[T](const T& a, const T& b)

    bint equalsEpsilon(real v1, real v2)
    void initSharedDir(const string& path)
    string getSharedDir()
    void unlinkShared(const string& name)

    cdef cppclass Ray

    cdef cppclass color:
        color()
        color(rgba c)
        color(float r,float g, float b, float a)
        color(const color& c)

        float r() const
        float g() const
        float b() const
        float a() const

        float r(float val)
        float g(float val)
        float b(float val)
        float a(float val)

        color interpolate(real val,const color& col) const

        bint operator == (const color & c) const
        bint operator != (const color & c) const
        bint operator < (const color & c) const
        bint operator > (const color & c) const

        color operator * (const color & c) const
        color operator * (real r) const
        color operator + (const color & c) const
        color operator + (real r) const
        color operator - (const color & c) const
        color operator - (real r) const


    cdef cppclass vec3:
        vec3()
        vec3(real val)
        vec3(real x, real y)
        vec3(real x, real y, real z)

        real x() const
        real y() const
        real z() const

        real x(real v)
        real y(real v)
        real z(real v)

        vec3 operator + (const vec3& v) const
        vec3 operator - (const vec3& v) const
        vec3 operator * (const vec3& v) const
        vec3 operator / (const vec3& v) const
        vec3 operator + (real v) const
        vec3 operator - (real v) const
        vec3 operator * (real v) const
        vec3 operator / (real v) const
        vec3 operator - () const

        vec3 abs() const
        vec3 inv() const
        vec3 sign() const
        vec3 cross(const vec3& v) const
        real dot(const vec3& v) const
        real len() const
        real lenSq() const
        vec3 norm() const
        real distTo(const vec3 & v) const
        real distToSq(const vec3 & v) const
        vec3 clamp(const vec3 v1,const vec3 v2) const
        void setMinVals(const vec3 &v)
        void setMaxVals(const vec3 &v)
        void normThis()
        real angleTo(const vec3 &v) const

        vec3 toPolar() const
        vec3 fromPolar() const

        vec3 toCylindrical() const
        vec3 fromCylindrical() const

        bint isZero() const

        bint operator < (const vec3 & v) const
        bint operator > (const vec3 & v) const
        bint operator == (const vec3 & v) const
        bint operator != (const vec3 &v) const

        bint inAABB(const vec3& minv, const vec3& maxv) const

        bint inOBB(const vec3& center, const vec3& hx, const vec3& hy, const vec3& hz) const

        bint onPlane(const vec3& planept, const vec3& planenorm) const

        bint inSphere(const vec3& center,real radius) const

        bint isInUnitCube(real margin) const
        
        bint isParallel(const vec3 &other) const

        vec3 planeNorm(const vec3& v2, const vec3& v3) const

        vec3 planeNorm(const vec3& v2, const vec3& v3, const vec3& farv) const

        real planeDist(const vec3& planept, const vec3& planenorm) const

        vec3 planeProject(const vec3& planept, const vec3& planenorm) const

        int planeOrder(const vec3& planenorm,const vec3& v1,const vec3& v2) const

        real lineDist(vec3 p1,vec3 p2) const

        real triArea(const vec3& b, const vec3& c) const

        vec3 lerp(real val,const vec3& v) const

        i32 hash() const
        
        @staticmethod
        vec3 X()
        
        @staticmethod
        vec3 Y()
        
        @staticmethod
        vec3 Z()


    cdef cppclass rotator:

        rotator()
        rotator(const rotator &r)
        rotator(real yaw, real pitch, real roll)
        rotator(real m00,real m01,real m02,real m10,real m11,real m12,real m20,real m21,real m22)
        rotator(const vec3& axis, real rads)
        rotator(const vec3& to, const vec3& fro)
        rotator(vec3 row1, vec3 col1, vec3 row2, vec3 col2)

        rotator(real x,real y, real z, real w)

        real w() const
        real x() const
        real y() const
        real z() const

        real getPitch() const
        real getYaw() const
        real getRoll() const

        vec3 operator * (const vec3 &v) const
        vec3 operator / (const vec3 &v) const

        rotator operator * (const rotator & r) const
        rotator operator + (const rotator & r) const

        bint operator == (const rotator & v) const
        bint operator != (const rotator &v) const

        rotator inverse() const

        rotator norm() const
        void normThis()
        
        void toMatrix(real v[16]) const

        i32 hash() const

    cdef cppclass transform:
        transform()
        transform(const vec3& trans,const vec3& scale,const rotator& rot,bint isInv)
        transform(real x, real y, real z, real sx, real sy, real sz, real yaw, real pitch, real roll, bint isInv)
        transform(const transform & t)

        vec3 getTranslation() const
        vec3 getScale() const
        rotator getRotation() const

        bint isInverse() const

        void setTranslation(const vec3 &v)
        void setScale(const vec3 &v)
        void setRotation(const rotator &r)

        vec3 operator * (const vec3 &v) const
        vec3 operator / (const vec3 &v) const
        Ray operator * (const Ray &r) const
        transform operator * (const transform& t) const

        bint operator == (const transform & t) const
        bint operator != (const transform & t) const

        transform inverse() const
        transform directional() const

        void toMatrix(real v[16]) const


    cdef cppclass Matrix[T]:
        Matrix(const char* name,const char* type,sval n, sval m,bint isShared) except +MemoryError
        Matrix(const char* name,const char* type,const char* sharedname,const char* serialmeta,sval n, sval m) except +MemoryError

        T* dataPtr() const

        bint hasMetaKey(const char* key) const
        vector[string] getMetaKeys() const
        string meta() const
        const char* meta(const char* key) const
        void meta(const char* key, const char* val)
        string serializeMeta() const
        void deserializeMeta(const string &s)

        Matrix[T]* clone(const char* newname, bint isShared) const

        const char* getName() const
        const char* getSharedName() const
        const char* getType() const

        void setName(const char* name)
        void setType(const char* type)

        bint isShared() const
        void setShared(bint val) except +MemoryError
        void clear() except +MemoryError
        sval n() const
        sval m() const
        sval memSize() const
        void fill(const T& t)

        void copyFrom[R](const Matrix[R]* r)

        Matrix[T]* subMatrix(const char* name,sval n, sval m,sval noff,sval moff,bint isShared) except +MemoryError const
        Matrix[T]* reshape(const char* name,sval n, sval m,bint isShared) except +MemoryError const

        void add[R](const R& t,sval minrow,sval mincol,sval maxrow,sval maxcol)
        void sub[R](const R& t,sval minrow,sval mincol,sval maxrow,sval maxcol)
        void mul[R](const R& t,sval minrow,sval mincol,sval maxrow,sval maxcol)
        void div[R](const R& t,sval minrow,sval mincol,sval maxrow,sval maxcol)

        void addm[R](const Matrix[R]& v,sval minrow,sval mincol,sval maxrow,sval maxcol)
        void subm[R](const Matrix[R]& v,sval minrow,sval mincol,sval maxrow,sval maxcol)
        void mulm[R](const Matrix[R]& v,sval minrow,sval mincol,sval maxrow,sval maxcol)
        void divm[R](const Matrix[R]& v,sval minrow,sval mincol,sval maxrow,sval maxcol)

#       void reorderColumns(const sval *orderinds) except +IndexError # unused? dangerous anyway
        void swapEndian()

        T& at(sval n, sval m) const
        const T& atc(sval n, sval m) const
        void ats(sval n, sval m, const T& t)
        T& operator () (sval n, sval m=0) const
        T& operator [] (sval n) const
        T getAt(sval n, sval m) except +IndexError const

        void setAt(const T& t, sval n, sval m) except +IndexError
        void setN(sval _newn) except +MemoryError
        void setM(sval _newm) except +MemoryError
        void addRows(sval num) except +MemoryError

        void reserveRows(sval num) except +MemoryError
        void append(Matrix[T] &t) except +MemoryError
        void append(const T& t,sval m) except +MemoryError
        void removeRow(sval n) except +

        void readBinaryFile(const char* filename,size_t offset) except +MemoryError
        void readTextFile(const char* filename,sval numHeaders) except +MemoryError
        void storeBinaryFile(const char* filename, int* header, sval headerlen) except +MemoryError
        indexpair indexOf(const T& t,sval aftern,sval afterm) const


    ctypedef Matrix[vec3] Vec3Matrix
    ctypedef Matrix[real] RealMatrix
    ctypedef Matrix[indexval] IndexMatrix
    ctypedef Matrix[color] ColorMatrix


    cdef cppclass Ray:
        Ray()
        Ray(const Ray& r)
        Ray(const vec3 &pos, const vec3 &dir) except +ValueError

        vec3 getPosition(real len) const
        vec3 getDirection() const

        void setPosition(vec3 &v)
        void setDirection(vec3 &v) except +ValueError

        real distTo(const vec3 v) const

        realpair intersectsAABB(const vec3& minv, const vec3& maxv) const
        realpair intersectsSphere(const vec3& center, real rad) const
        realpair intersectsRay(const Ray& ray) const
        real intersectsLineSeg(const vec3& v1, const vec3& v2) const
        real intersectsPlane(const vec3 & planepos, const vec3 & planenorm) const

        realtriple intersectsTri(const vec3& v0, const vec3& v1, const vec3& v2)

        vector[indextriple] intersectsTriMesh(const Vec3Matrix* nodes, const IndexMatrix* inds,const Vec3Matrix* centers, const RealMatrix* radii2, sval numResults,sval excludeInd) except +IndexError const


    cdef cppclass Config:
        Config()

        void set(const char* group, const char* name, const char* value)
        void set(const char* name, const char* value)
        bint hasValue(const char* group, const char* name) const
        const char* get(const char* group, const char* name)
        const char* get(const char* name)

        string toString()


    cdef cppclass VertexBuffer:
        vec3 getVertex(int i) const
        vec3 getNormal(int i) const
        color getColor(int i) const
        vec3 getUVWCoord(int i) const

        sval numVertices() const
        bint hasNormal() const
        bint hasColor() const
        bint hasUVWCoord() const


    cdef cppclass IndexBuffer:
        sval numIndices() const
        sval indexWidth(int i) const
        sval getIndex(int i,int w) const


    cdef cppclass MatrixVertexBuffer(VertexBuffer):
        MatrixVertexBuffer(Vec3Matrix* vecs,ColorMatrix* cols,IndexMatrix* extinds) except+


    cdef cppclass MatrixIndexBuffer(IndexBuffer):
        MatrixIndexBuffer(IndexMatrix* indices,IndexMatrix* extinds)


    cdef cppclass Vec3Curve:
        Vec3Curve(bint isXFunc)
        void addCtrlPoint(const vec3& t)
        void setCtrlPoint(const vec3& t,indexval index) except +IndexError
        void removeCtrlPoint(indexval index) except +IndexError
        sval numPoints() const
        vec3 getCtrlPoint(indexval index) except +IndexError const
        vec3 at(real tt) const
        real atX(real x, real threshold) const


    cdef cppclass Spectrum:
        Spectrum(const string& name)
        
        const char* getName()
        
        void clearSpectrum()
        
        void copySpectrumFrom(const Spectrum* s)
        
        void addSpectrumValue(real pos,color value)
        sval numSpectrumValues() const
        indexval getSpectrumIndex(real pos,color value) const
        color interpolateColor(real pos) const
        void removeSpectrumValue(int index) except +IndexError
        real getSpectrumPos(int index) except +IndexError const
        color getSpectrumValue(int index) except +IndexError const
        void setSpectrumValue(sval index, real pos,color value) except +IndexError

        sval numAlphaCtrls() const
        vec3 getAlphaCtrl(indexval index) except +IndexError const
        void addAlphaCtrl(vec3 v)
        void removeAlphaCtrl(indexval index) except +IndexError
        void setAlphaCtrl(vec3 v, indexval index) except +IndexError

        void setLinearAlpha(bint b)
        bint isLinearAlpha() const

        void fillColorMatrix(ColorMatrix *col,const RealMatrix *mat,bint useValAsAlpha) except +IndexError
        

    cdef cppclass Material(Spectrum):
        Material* clone(const char* name) const
        void copyTo(Material* mat,bint copyTex,bint copySpec,bint copyProgs) const

        real getAlpha() const
        void setAlpha(real alpha)

        bint usesInternalAlpha() const
        void useInternalAlpha(bint val)

        color getAmbient() const
        color getDiffuse() const
        color getSpecular() const
        color getEmissive() const

        real getShininess() const
        real getPointSizeMin() const
        real getPointSizeMax() const
        real getPointSizeAbs() const
        bint usesPointAttenuation() const
        BlendMode getBlendMode() const

        bint usesVertexColor() const
        bint usesLighting() const
        bint usesFlatShading() const
        bint usesDepthCheck() const
        bint usesDepthWrite() const
        bint usesTexFiltering() const
        bint isClampTexAddress() const
        bint isCullBackfaces() const
        bint usesPointSprites() const
        const char* getTexture() const
        const char* getGPUProgram(ProgramType pt) const

        bint isTransparentColor() const

        void setAmbient(const color & c)
        void setDiffuse(const color & c)
        void setSpecular(const color & c)
        void setEmissive(const color & c)
        void setShininess(real c)
        void setPointSize(real min,real max)
        void setPointSizeAbs(real size)
        void setPointAttenuation(bint enabled,real constant,real linear, real quad)
        void setBlendMode(BlendMode bm)
        void useVertexColor(bint use)
        void useLighting(bint use)
        void useFlatShading(bint use)
        void useDepthCheck(bint use)
        void useDepthWrite(bint use)
        void useTexFiltering(bint use)
        void clampTexAddress(bint use)
        void cullBackfaces(bint cull)
        void usePointSprites(bint useSprites)
        void setTexture(const char* name)
        #void setTexture(const Texture* tex) # need to have differing number of args to tell overrides apart?
        void useSpectrumTexture(bint use)
        void setGPUProgram(const char* name, ProgramType pt)
        void setGPUProgram(const GPUProgram *prog)

        bint setGPUParamInt(ProgramType pt,const string& name, int val)
        bint setGPUParamReal(ProgramType pt,const string& name, real val)
        bint setGPUParamVec3(ProgramType pt,const string& name, vec3 val)
        bint setGPUParamColor(ProgramType pt,const string& name, color val)


    cdef cppclass Light:
        void setPosition(vec3 &v)
        void setDirection(vec3 &v)
        void setDiffuse(const color & c)
        void setSpecular(const color & c)

        void setDirectional()
        void setPoint()
        void setSpotlight(real radsInner, real radsOuter, real falloff)
        void setAttenuation(real range, real constant,real linear, real quad)

        void setVisible(bint isVisible)
        bint isVisible() const


    cdef cppclass Image:
        TextureFormat getFormat() const
        sval getWidth() const
        sval getHeight() const
        sval getDepth() const
        size_t getDataSize() const
        u8* getData() 
        string encode(const string& format)
        void fillRealMatrix(RealMatrix* mat) except +IndexError
        void fillColorMatrix(ColorMatrix* mat) except +IndexError


    cdef cppclass Camera:
        const char* getName() const

        real getAspectRatio() const

        Ray* getProjectedRay(real x, real y, bint isAbsolute)

        vec3 getPosition()
        vec3 getLookAt()
        rotator getRotation()

        vec3 getScreenPosition(vec3 pos)
        vec3 getWorldPosition(real x, real y, bint isAbsolute) const

        void setPosition(const vec3 &v)
        void setLookAt(const vec3 &v)
        void setUp(const vec3 & v)
        void setZUp()
        void rotate(const rotator & r)
        void setRotation(const rotator& r)

        void setNearClip(real dist)
        void setFarClip(real dist)
        void setVertFOV(real rads)
        void setBGColor(const color & c)
        void setAspectRatio(real rat)
        void setViewport(real left,real top,real width,real height)
        void setOrtho(bint isOrtho)
        void setWireframe(bint isWireframe)

        real getVertFOV() const

        real getNearClip() const
        real getFarClip() const

        sval getWidth() const
        sval getHeight() const

        bint isPointInViewport(int x, int y) const

        void setSecondaryCamera(bint secondary)

        bint isSecondaryCamera()

        void renderToFile(const string& filename,sval width,sval height, TextureFormat format,real stereoOffset) except+
        void renderToStream(void* stream,sval width,sval height, TextureFormat format,real stereoOffset) except+
        Image* renderToImage(sval width,sval height, TextureFormat format,real stereoOffset) except+
        

    cdef cppclass Figure:
        const char* getName()
        void setPosition(const vec3 &v)
        void setRotation(const rotator& r)
        void setScale(const vec3 &v)
        void setTransform(const vec3 &trans,const vec3 &scale, const rotator &rot)
        void setTransform(const transform &trans)
        void setMaterial(const char* mat) except+
#       void setMaterial(const Material *mat) except+ # can't differentiate overloads by arg type, only arg num?

        const char* getMaterial() const
        pair[vec3,vec3] getAABB() const

        void fillData(const VertexBuffer* vb, const IndexBuffer* ib,bint deferFill,bint doubleSided) except+
        void setVisible(bint isVisible)
        bint isVisible() const

        bint isTransparent() const
        bint isOverlay() const
        sval getRenderQueue() const

        void setTransparent(bint isTrans)
        void setOverlay(bint isOverlay)

        void setRenderQueue(sval queue)

        void setCameraVisibility(const Camera* cam, bint isVisible)

        void setParent(Figure *fig)

        vec3 getPosition(bint isDerived) const
        vec3 getScale(bint isDerived) const
        rotator getRotation(bint isDerived) const
        transform getTransform(bint isDerived) const


    cdef cppclass BBSetFigure(Figure):
        void setDimension(real width, real height)

        real getWidth() const
        real getHeight() const

        void setUpVector(const vec3& v)

        int numBillboards()

        void setBillboardPos(indexval index, const vec3& pos) except +IndexError
        void setBillboardDir(indexval index, const vec3& dir) except +IndexError
        void setBillboardColor(indexval index, const color& col) except +IndexError


#   cdef cppclass InterpolateFigure(Figure):
#       void interpolate(real val,Figure *f1, Figure* f2) except+
#       void initialize(Figure *f1) except+

    cdef cppclass RibbonFigure(Figure):
        void setOrientation(const vec3& orient) 
        bint isCameraOriented()
        vec3 getOrientation() 
    
        void setNumRibbons(sval num) 
        sval numRibbons() 
        sval numNodes(sval ribbon) except +IndexError
        void setMaxNodes(sval num)
        sval getMaxNodes() 
        
        void clearRibbons() 
        void removeRibbon(sval ribbon) except +IndexError
        void removeNode(sval ribbon) except +IndexError
        void addNode(sval ribbon,const vec3& pos, const color& col,real width, const rotator& rot, real tex) except +IndexError
        void setNode(sval ribbon,sval node,const vec3& pos, const color& col,real width, const rotator& rot, real tex) except +IndexError
        vec3 getNode(sval ribbon,sval node) except +IndexError
        quadruple[color,real,rotator,real] getNodeProps(sval ribbon,sval node) except +IndexError
        

    cdef cppclass TextureVolumeFigure(Figure):
        void setNumPlanes(sval num)
        sval getNumPlanes() const

        void setAlpha(real a)
        real getAlpha() const

        void setTexAABB(const vec3& minv, const vec3& maxv)

        void setAABB(const vec3& minv, const vec3& maxv)

        vec3 getTexXiPos(vec3 pos) const
        vec3 getTexXiDir(vec3 pos) const
        sval getPlaneIntersects(vec3 planept, vec3 planenorm,vec3 vbuffer[6][2],bint transformPlane,bint isXiPoint)


    cdef cppclass GlyphFigure(Figure):
        void setGlyphScale(vec3 v)
        vec3 getGlyphScale() const

        void setGlyphName(const string& name)
        string getGlyphName() const

        void addGlyphMesh(const string& name,const Vec3Matrix* nodes,const Vec3Matrix* norms, const IndexMatrix* inds)
        
        
    cdef cppclass TextFigure(Figure):
        void setText(const string& text)
        void setFont(const string& fontname) except+
        void setColor(const color& col)
        
        void setVAlign(VAlignType align)
        void setHAlign(HAlignType align)
        void setTextHeight(real height)
        void setSpaceWidth(real width)
        
        string getText() const 
        string getFont() const
        color getColor() const
        
        VAlignType getVAlign() const
        HAlignType getHAlign() const 
        real getTextHeight() const
        real getSpaceWidth() const


    cdef cppclass Texture:
        const char* getName() const
        const char* getFilename() const
        sval getWidth() const
        sval getHeight() const
        sval getDepth() const
        bint hasAlpha() const
        TextureFormat getFormat() const
        void fillBlack()
        void fillColor(color col)
        void fillColor(const ColorMatrix *mat,indexval depth)
        void fillColor(const RealMatrix *mat,indexval depth,real minval,real maxval, const Material* colormat,const RealMatrix *alphamat,bint mulAlpha)


    cdef cppclass GPUProgram:
        string getName() const
        void setType(ProgramType pt)
        ProgramType getType() const
        string getLanguage() const
        void setLanguage(const string& lang)
        void setSourceCode(const string& code)
        bint hasError() const
        string getSourceCode() const
        bint setParameter(const string& param, const string& val)
        string getParameter(const string& param) const
        string getEntryPoint() const
        string getProfiles() const
        vector[string] getParameterNames() const
        void setEntryPoint(const string& main)
        void setProfiles(const string& profiles)


    cdef cppclass RenderScene:

        Camera* createCamera(const char* name,real left,real top,real width,real height) except+
        void setAmbientLight(const color & c)
        void addResourceDir(const char* dir)
        void initializeResources()
        Material* createMaterial(const char* name) except+
        Figure* createFigure(const char* name, const char* mat,FigureType type) except+
        Light* createLight() except+
        Image* loadImageFile(const string &filename) except+
        Texture* loadTextureFile(const char* name,const char* absFilename) except+
        Texture* createTexture(const char* name,sval qwidth, sval height, sval depth, TextureFormat format) except+
        GPUProgram* createGPUProgram(const char* name,ProgramType ptype,const char* language) except+
        void saveScreenshot(const char* filename,Camera* c,int width,int height,real stereoOffset,TextureFormat tf) except+
        Config* getConfig() const

        void logMessage(const char* msg)

        void setBGObject(color col,bint enabled)

        void setRenderHighQuality(bint val)
        bint getRenderHighQuality() const

        void setAlwaysHighQuality(bint val)
        bint getAlwaysHighQuality() const


    cdef cppclass RenderAdapter:
        u64 createWindow(int width, int height) except+
        void paint()
        void resize(int x, int y,int width, int height)

        RenderScene* getRenderScene()


    # entry point for binding to Ogre, this function is implemented in OgreRenderTypes.*
    RenderAdapter* getRenderAdapter(Config* config) except+

    void basis_Tet1NL(real xi0, real xi1, real xi2,real* coeffs)
    void basis_Hex1NL(real xi0, real xi1, real xi2, real* coeffs)
    real basis_n_NURBS(sval ctrlpt,sval degree, real xi,const RealMatrix* knots)
    void basis_NURBS_default(real u, real v, real w,sval ul, sval vl, sval wl, sval udegree, sval vdegree, sval wdegree,real* coeffs)

    bint pointInTet(vec3 pt, vec3 n1, vec3 n2, vec3 n3, vec3 n4)
    bint pointInHex(vec3 pt, vec3 n1, vec3 n2, vec3 n3, vec3 n4, vec3 n5, vec3 n6, vec3 n7, vec3 n8)
    vec3 pointSearchLinTet(vec3 pt, vec3 n1, vec3 n2, vec3 n3, vec3 n4)
    vec3 pointSearchLinHex(vec3 pt, vec3 n1, vec3 n2, vec3 n3, vec3 n4, vec3 n5, vec3 n6, vec3 n7, vec3 n8)

    float calculateTetVolume(vec3 a, vec3 b, vec3 c, vec3 d)

    pair[vec3,vec3] calculateBoundBox(const Vec3Matrix* mat)

    quadruple[int,int,int,int] calculateBoundSquare[T](const Matrix[T]* mat, const T& threshold)

    vector[vec3] findBoundaryPoints[T](const Matrix[T]* mat, T threshold)

    sval countValuesInRange(const RealMatrix* mat, real minv,real mavx)

    real sumMatrix(const RealMatrix* mat)

    #realpair minmaxMatrix(const RealMatrix* mat)
    pair[T,T] minmaxMatrix[T](const Matrix[T]* mat)

    real trilerpMatrices(const RealMatrix* mat1, const RealMatrix* mat2, vec3 v1, vec3 v2)

    vec3 getPlaneXi(const vec3& pos, const vec3& planepos, const rotator& orientinv, const vec3& dimvec)

    void interpolateImageStack(const vector[RealMatrix*]& stack,const transform& stacktransinv,RealMatrix *out,const transform& outtrans)

    real getImageStackValue(const vector[RealMatrix*]& stack,const vec3& pos)

    void calculateImageHistogram(const RealMatrix* img, RealMatrix* hist, i32 minv)

    realtriple calculateTriPlaneSlice(const vec3& planept, const vec3& planenorm, const vec3& a, const vec3& b, const vec3& c)

    real calculateLinePlaneSlice(const vec3& planept, const vec3& planenorm, const vec3& a, const vec3& b)

    void calculateTetValueIntersects(real val, real a, real b, real c, real d,real* vals)

    sval calculateHexValueIntersects(real val,real* vals,intersect* results)


cdef extern from "RenderTypes.h" namespace "RenderTypes":
    cdef cppclass CallbackVertexBuffer[T](VertexBuffer):
        CallbackVertexBuffer(T context, sval numvertices, vec3 (*vertfunc)(T,int) , vec3 (*normalfunc)(T,int) , color (*colorfunc)(T,int), vec3 (*uvwfunc)(T,int) )


    cdef cppclass CallbackIndexBuffer[T](IndexBuffer):
        CallbackIndexBuffer(T context, sval numindices, sval (*widthfunc)(T,int),sval (*indexfunc)(T,int,int))

