#   Copyright (c) 2016, Xilinx, Inc.
#   All rights reserved.
# 
#   Redistribution and use in source and binary forms, with or without 
#   modification, are permitted provided that the following conditions are met:
#
#   1.  Redistributions of source code must retain the above copyright notice, 
#       this list of conditions and the following disclaimer.
#
#   2.  Redistributions in binary form must reproduce the above copyright 
#       notice, this list of conditions and the following disclaimer in the 
#       documentation and/or other materials provided with the distribution.
#
#   3.  Neither the name of the copyright holder nor the names of its 
#       contributors may be used to endorse or promote products derived from 
#       this software without specific prior written permission.
#
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#   AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, 
#   THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR 
#   PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR 
#   CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, 
#   EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, 
#   PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
#   OR BUSINESS INTERRUPTION). HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
#   WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR 
#   OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF 
#   ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

__author__      = "Anurag Dubey"
__copyright__   = "Copyright 2016, Xilinx"
__email__       = "pynq_support@xilinx.com"

import os
import signal
import sys
import cffi
import resource

if os.getuid() != 0:
    raise RuntimeError("Root permission needed by the library.")

# Cleanup on Segfaults
def sig_handler(signum, frame):
    print("Invalid Memory Access!")
    xlnk().xlnk_reset()
    sys.exit(127)
signal.signal(signal.SIGSEGV, sig_handler)

ffi = cffi.FFI()

ffi.cdef("""
static uint32_t xlnkBufCnt = 0;
uint32_t cma_mmap(uint32_t phyAddr, uint32_t len);
uint32_t cma_munmap(void *buf, uint32_t len);
void *cma_alloc(uint32_t len, uint32_t cacheable);
uint32_t cma_get_phy_addr(void *buf);
void cma_free(void *buf);
uint32_t cma_pages_available();
void _xlnk_reset();
""")

libxlnk = ffi.dlopen("/usr/lib/libsds_lib.so")

class xlnk:
    """Class to enable CMA memory management.

    The CMA state maintained by this class is local to the 
    application except for the `CMA Memory Available` attribute
    which is global across all the applications.

    Attributes
    ----------
    bufmap : dict
        Mapping of allocated memory to the buffer sizes in bytes.
        
    """
    def __init__(self):
        """Initialize new xlnk object.

        Parameters
        ----------
        None

        Returns
        -------
        None

        """
        self.bufmap = {}

    def __del__(self):
        """Destructor for the current xlnk object.

        Frees up all the memory which was allocated through current object.

        Parameters
        ----------
        None

        Returns
        -------
        None

        """
        for key in self.bufmap.keys():
            libxlnk.cma_free(key)
    
    def __check_buftype(self, buf):
        """Internal method to check for a valid buffer.
        
        Parameters
        ----------
        buf : cffi.FFI.CData
            A valid buffer object which was allocated through `cma_alloc`.
            
        Returns
        -------
        None
            
        """
        if "cdata" not in str(buf):
            raise RuntimeError("Unknown buffer type")
        
    def cma_alloc(self, length, cacheable = 0, data_type = "void"):
        """Allocate physically contiguous memory buffer.

        Allocates a new buffer and adds it to `bufmap`.
        
        Possible values for parameter `cacheable` are:
        
        `1`: the memory buffer is cacheable.
        
        `0`: the memory buffer is non-cacheable.

        Examples
        --------
        memmanager = xlnk.xlnk()

        # Allocate 10 `void *` memory locations.
        
        m1 = memmanager.cma_alloc(10)

        # Allocate 10 `float *` memory locations.
        
        m2 = memmanager.cma_alloc(10, data_type = "float")

        Notes
        -----
        1. Total size of buffer is automatically calculated as
        size = length * sizeof(data_type)

        2. This buffer is allocated inside the kernel space using
        xlnk driver. The maximum allocatable memory is defined
        at kernel build time using the CMA memory parameters.
        For Pynq-Z1 kernel, it is specified as 128MB.
        
        The unit of `length` depends upon the `data_type` argument.
        
        Parameters
        ----------
        length : int
            Length of the allocated buffer. Default unit is bytes.
        cacheable : int
            Indicating whether or not the memory buffer is cacheable.
        data_type : str
            CData type of the allocated buffer. Should be a valid C-Type.
        
        Returns
        -------
        cffi.FFI.CData
            An CFFI object which can be accessed similar to arrays.
            
        """
        if data_type != "void":
            length = ffi.sizeof(data_type) * length
        buf = libxlnk.cma_alloc(length, cacheable)
        if buf == ffi.NULL:
            raise RuntimeError("Failed to allocate Memory!")
        self.bufmap[buf] = length
        return ffi.cast(data_type+"*",buf)
        
    def cma_get_buffer(self, buf, length):
        """Get a buffer object.
        
        Used to get an object which supports python buffer interface. 
        The return value thus, can be cast to objects like
        `bytearray`, `memoryview` etc.

        Parameters
        ----------
        buf : cffi.FFI.CData
            A valid buffer object which was allocated 
            through `cma_alloc`.
        len : int
            Length of buffer in Bytes.
            
        Returns
        -------
        cffi.FFI.CData
            A CFFI object which supports buffer interface.

        """
        self.__check_buftype(buf)
        return(ffi.buffer(buf, length))
    
    def cma_get_phy_addr(self, buf_ptr):
        """Get the physical address of a buffer.
        
        Used to get the physical address of a memory buffer allocated with
        `cma_alloc`. The return value can be used to access the buffer from the
        programmable logic.

        Parameters
        ----------
        buf_ptr : cffi.FFI.CData
            A void pointer pointing to the memory buffer. Return value of
            `cma_alloc`.
            
        Returns
        -------
        unsigned int
            The physical address of the memory buffer.

        """
        self.__check_buftype(buf_ptr)
        if "void *" not in str(buf_ptr):
            raise RuntimeError("Unkown pointer type")
        return(libxlnk.cma_get_phy_addr(buf_ptr))

    @staticmethod
    def cma_memcopy(dest, src, nbytes):
        """High speed memcopy between buffers.

        Used to perform a byte level copy of data from source buffer to 
        the destination buffer.

        Parameters
        ----------
        dest : cffi.FFI.CData
            Destination buffer object which was allocated through `cma_alloc`.
        src : cffi.FFI.CData
            Source buffer object which was allocated through `cma_alloc`.
        nbytes : int
            Number of bytes to copy.

        Returns
        -------
        None

        """
        ffi.memmove(dest, src, nbytes)
    
    @staticmethod
    def cma_cast(data, data_type = "void"):
        """Cast underlying buffer to a specific C-Type.
    
        Input buffer should be a valid object which was allocated through 
        `cma_alloc` or a CFFI pointer to a memory buffer. Handy for changing 
        void buffers to user defined buffers.
    
        Parameters
        ----------
        data : cffi.FFI.CData
            A valid buffer pointer allocated via `cma_alloc`.
        data_type : str
            New data type of the underlying buffer.
        
        Returns
        -------
        cffi.FFI.CData
            Pointer to buffer with specified data type.
            
        """
        return ffi.cast(data_type+"*", data)
      
    def cma_free(self, buf):
        """Free a previously allocated buffer.
       
        Input buffer should be a valid object which was allocated through 
        `cma_alloc` or a CFFI pointer to a memory buffer.
        
        Parameters
        ----------
        buf : cffi.FFI.CData
            A valid buffer pointer allocated via `cma_alloc`.

        Returns
        -------
        None

        """
        if buf in self.bufmap:
            self.bufmap.pop(buf, None)
        self.__check_buftype(buf)
        libxlnk.cma_free(buf)
    
    def cma_stats(self):
        """Get current CMA memory Stats.

        `CMA Memory Available` : Systemwide CMA memory availability.
        
        `CMA Memory Usage` : CMA memory used by current object.
        
        `Buffer Count` : Buffers allocated by current object.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary of current stats.

        """
        stats = {}
        free_pages = libxlnk.cma_pages_available()
        stats['CMA Memory Available'] = resource.getpagesize() * free_pages
        memused = 0
        for key in self.bufmap:
            memused += self.bufmap[key]
        stats['CMA Memory Usage'] = memused
        stats['Buffer Count'] = len(self.bufmap)
        return stats

    def xlnk_reset(self):
        """Systemwide Xlnk Reset.

        Notes
        -----
        This method resets all the CMA buffers allocated across the system.

        Parameters
        ----------
        None

        Returns
        -------
        None

        """
        self.bufmap = {}
        libxlnk._xlnk_reset()