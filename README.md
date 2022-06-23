# FGPU_PYNQ

This repo includes a PYNQ package that uses the FGPU as an overlay that can be used to offload computations of a program to a soft-core GPU.

### Compatible boards:
We are providing ready to use bitstreams for the PYNQ-Z2 board, Zedboard, and the ZC706. Other boards with a 32-bit ARM processor are also compatible, but the user has to create their own bitstream. Please refeer to our [FGPU repository](https://github.com/CEatBTU/FGPU.git) for instructions on how to create a custom bitstream with the provided scripts.

Other boards like Ultrascale+ (with 64-bit ARM processors) are not yet fully compatible. We are working on porting the LLVM compiler which is the only non-compatible feature yet. The user can still use these types of boards, provided that they compile the openCL kernels on their own using our [FGPU compiler](https://github.com/CEatBTU/FGPU_Compiler.git).

### Pre-requisits:
The user needs to have a board with a PYNQ image already running. 

### Use:
1. Download the sources and place them preferably inside the jupyter notebooks folder.
2. Open the desired jupyter notebook and run each cell taking notice of the paths which might need to be adapted directly by the user to fit their own paths.
3. Under the Download bitstream cell, select the bitstream that fits the board that is being used.

If the user wants to run their own application it is advised to use one of the notebooks as templates, and modify the openCL kernel that the FGPU has to execute, and the parameters that needs to be adapted to fit the application.


NOTE: the median example might not work out-of-the-box due to recent changes to opencv packages.
