# Eidolon

Eidolon is a biomedical visualization and analysis framework designed to render 
spatial biomedical data (images and meshes) and provide facilities for image reconstruction, 
analysis, and computation. Implemented in Python with rendering provided by the Ogre3D engine, 
Eidolon presents a powerful workbench environment for Windows, OSX, and Linux.

## Visualize Data

| Meshes<br>![](mesh2.png) | Images<br> ![](image1.png) | Combined<br> ![](meshimage1.png) |

Eidolon can visualize mesh and image data in 3D, rendering multiple mesh fields and representations with images in the same environment.
Spatial information stored in files is respected thus ensuring spatial relationships are correct.
Many popular file formats are supported (VTK, NIfTI, Dicom, MetaImage).

## View Images in 2D

| Single Image<br>![](2ch.png) | Multiple Images<br>![](sala5.png) | Image and Mesh<br> ![](meshimage20032.png)|

Create 2D views in Eidolon to visualize individual image planes and the data they intersect with.
Meshes passing through images can be visualized as isolines, and other images can be overlaid to allow the user to assess spatial correlation.

## Visualize in Time

| Meshes<br>![](meshanim1.gif) | Images<br> ![](imageanim1.gif) | Combined<br> ![](meshimageanim1.gif) |

Mesh and image data which is time dependent can be rendered in Eidolon simultaneously.
Timing information is read from input data to ensure data correlates temporally during playback.

## Process Data

| Script Interface<br>![](script1.png) | Python Console<br>![](console.png)  | Image Processing Projects<br>![](project.png) |

Eidolon exposes its internal data structures and algorithms to user scripts which can be loaded at runtime.
This allows custom processing of loaded data to be performed which can import additional libraries.
The runtime Python console allows users to probe and experiment with loaded data, allowing Eidolon to function as a workbench environment.
Image processing projects expose IRTK/MIRTK functionality for image registration, alignment, motion tracking, and other image processing tasks. 

## Extend Platform

| Custom Code<br>![](code.png) | Custom UI<br>![](customui.png) | Plugin Interface<br>![](plugin2.png)|

Write custom modules and scripts to extend the capabilities of Eidolon. 
New user interfaces can be easily imported using PyQt to provide custom interactive components.
The plugin-oriented architecture allows the extension of virtually all aspects of the platform, permitting new
plugins to be created to import file formats, implement algorithms, and process data.

## Screenshots

<div class="slide-container">
<a class="slide-btn display-left" onclick="plusDivs(-1)">&#10094;</a>
<a class="slide-btn display-right" onclick="plusDivs(1)">&#10095;</a>

	<div class="slide">
	  <img src="screen1.png" class="slide-img">
	  <div class="slide-txt">Cardiac mesh with fields</div>
	</div>
	
	<div class="slide">
	  <img src="screen2.png" class="slide-img">
	  <div class="slide-txt">Cardiac mesh rendered with images</div>
	</div>
	
	<div class="slide">
	  <img src="screen3.png" class="slide-img">
	  <div class="slide-txt">Eidolon interface</div>
	</div>
	
	<div class="slide">
	  <img src="screen4.png" class="slide-img">
	  <div class="slide-txt">Segmentation interface</div>
	</div>
</div>

<script>
var slideIndex = 0;
showDivs(slideIndex);

function plusDivs(n) { showDivs(slideIndex += n); }

function showDivs(n) {
    var i;
    var x = document.getElementsByClassName("slide");
    if (n >= x.length) {slideIndex = 0} 
    if (n < 0) {slideIndex = x.length-1} ;
    for (i = 0; i < x.length; i++) {
        x[i].style.display = "none"; 
    }
    x[slideIndex].style.display = "block"; 
}
</script>

---

| ![](python-powered-w-140x56.png) | ![](Ogre-logo.png) | ![](Python_and_Qt.png) | ![](numpyscipy.png) | ![](kcl.png) | 

Copyright (c) 2016 Eric Kerfoot <eric.kerfoot@kcl.ac.uk>, King's College London, all rights reserved