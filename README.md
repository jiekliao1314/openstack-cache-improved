# openstack-cache-improved
**openstack-cache-improved** aims to improve the OpenStack image cache system in compute nodes.

**The main work includes the following four aspects:** 
1. It is found that qcow2 image format is easy to be segmented, shared and compressed. The two-layers image in common cloud computing can be changed to three-layers image with the trade-off between flexibility and performance. On the one hand, three-layers image will meet the user's need of customizing image file by increasing the layers of image. On the other hand, because of more sharing data it can further optimize the image strorage and distribution. Evaluation shows that qcow2-qcow2-qcow2 image type has obvious advantages compared with two-layers image.

2. Design and implement prefetching image cache mechanism based on OpenStack. The algorithm can assure image cache distribution planned in advance on compute nodes. The mechanism can not only prefetch image cache at the beginning of the cloud deployment or extension of compute nodes, but also controll the transmission and alleviate performance problems caused by image library bottleneck before large-scale deployment of virtual machine.It will avoid the collapse of a cloud platform and burst error. The test results show its good performance. 

3. Design and implement image cache management based on OpenStack. To improving the original one , the new image caching mechanism designs a reasonable image cache replacement algorithm and enhances the limitation of space used by image cache storage on compute nodes. The mechanism improves the image cache utilization and significantly decrease the average image transmission as well as avoiding excessive comsumption of image cache. Evaluation depicts that the algorithm perform stably and accelerate the virtual machine deployment perfectly. 

4. Design and implement virtual machine deployment scheduling by image cache based on OpenStack. The mechanism fully considers the distribution of image cache and cluster load balance when scheduling and it can further reduce the necessity of the image file to download. The test found that the mechanism under various concurrency is stable and reliable and can significantly reduce the virtual machine deployment time. 

