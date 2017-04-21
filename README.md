# GMTB CCPP
[GMTB](http://www.dtcenter.org/GMTB/html/) Common Community Physics Package
(CCPP), including the Interoperable Physics Driver (IPD).

[![Build Status](https://travis-ci.org/t-brown/ccpp.svg?branch=master)](https://travis-ci.org/NCAR/gmtb-ccpp)
[![Coverage Status](https://coveralls.io/repos/github/t-brown/ccpp/badge.svg?branch=master)](https://coveralls.io/github/NCAR/gmtb-ccpp?branch=master)

## Requirements
1. Compilers for example the [GNU Compiler Collection](https://gcc.gnu.org/)
  * C
  * Fortran (must be 2003 compliant)
2. [Cmake](https://cmake.org)

## Building
It is recommend to do an out of source build.

1. Clone the repository.
  * `git clone https://github.com/t-brown/ccpp`
2. Change into the repository clone
  * `cd ccpp`
3. Specify the compiler to use. For example the GNU compiler.
  * `ml gcc`
  * `export CC=gcc`
  * `export FC=gfortran`
  * `export CXX=g++`
4. Make a build directory and change into it.
  * `mkdir build`
  * `cd build`
5. Create the makefiles.
  * `cmake ..`
5. Build the CCPP library and test programs.
  * `make`

## Running Tests
There are a few test programs within the `ccpp/src/tests` directory.
These should be built when the CCPP library is compiled.

To run the tests you have to add the check scheme library (`libcheck.so`)
to your `LD_LIBRARY_PATH` (`DYLD_LIBRARY_PATH` for OS X).
```
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:$(pwd)/schemes/check/src/check-build/
```

Then issue the following within the build directory.
  * `make test`

All tests should pass, if not, please open an issue. The output should be
similar to:
```
Running tests...
Test project /home/tbrown/Sources/gmtb-ccpp/build
    Start 1: XML_1
1/8 Test #1: XML_1 ............................   Passed    0.02 sec
    Start 2: XML_2
2/8 Test #2: XML_2 ............................   Passed    0.01 sec
    Start 3: XML_3
3/8 Test #3: XML_3 ............................   Passed    0.01 sec
    Start 4: XML_4
4/8 Test #4: XML_4 ............................   Passed    0.01 sec
    Start 5: XML_5
5/8 Test #5: XML_5 ............................   Passed    0.00 sec
    Start 6: XML_6
6/8 Test #6: XML_6 ............................   Passed    0.00 sec
    Start 7: FIELDS
7/8 Test #7: FIELDS ...........................   Passed    0.00 sec
    Start 8: CHECK
8/8 Test #8: CHECK ............................   Passed    0.01 sec

100% tests passed, 0 tests failed out of 8

Total Test time (real) =   0.08 sec
```

## Validating XML
A suite is defined in XML. There is a test suite definied within
the `tests` directory, there is also the XML Schema Definition in
that directory too. To validate a new test suite, you can use
`xmllint`. For example to validate `suite_RAP.xml`:
```
xmllint --schema suite.xsd --noout suite_RAP.xml
suite_RAP.xml validates
```

Within the `src/tests` directoty there is `test_init_fini.f90` which
will get built when the CCPP library is built. This program only calls
  * `ccpp_init()`
  * `ccpp_fini()`
It is a program to check the suite XML validation within the CCPP
library. The following is an example of using it from within the
`build` directory.
```
src/tests/test_init_fini my_suite.xml
```

## Physics Schemes
All physics schemes are kept in the repository under the `schemes`
directory.

To add a new scheme one needs to

1. Add/Create the scheme within `schemes`. You should create a
   sub-directory under the `schemes` directory. You will need to
   add a [`ExternalProject_Add()`](https://cmake.org/cmake/help/latest/module/ExternalProject.html).
   call to the `schemes/CMakeLists.txt` file.
2. Create a `cap` subroutine. The IPD will call your
   cap routine.

  a. The cap routine must be labelled "schemename_cap".
     For example, the dummy scheme has a cap called
     "dummy_cap". The requirements are that it is
    1. Lowercased
    2. "_cap" is appended.
  b. Map all the inputs for the cap from the `cdata` encapsulating
     type (this is of the `ccpp_t` type). The cap will extract the
     fields from the fields array with the `ccpp_fields_get()`
     subroutine.

An example of a scheme that does nothing is `schemes/check/test.f90`.

## Usage
The CCPP must first be initialized, this is done by calling `ccpp\_init()`.
Once initialized, all variables that will be required in a physics scheme
have to be added to the ccpp data object (of type `ccpp_t`). These variables
can later be retrieved in a physics schemes cap.

Example usage, in an atmosphere component:
```
type(ccpp_t), target :: cdata
character(len=128)   :: scheme_xml_filename
integer              :: ierr

ierr = 0

! Initialize the CCPP and load the physics scheme.
call ccpp_init(scheme_xml_filename, cdata, ierr)
if (ierr /= 0) then
    call exit(1)
end if

! Add surface temperature (variable surf_t).
call ccpp_fields_add(cdata, 'surface_temperature', surf_t, ierr, 'K')
if (ierr /= 0) then
    call exit(1)
end if

! Call the first physics scheme
call ccpp_ipd_run(cdata%suite%ipds(1)%subcycles(1)%schemes(1), cdata, ierr)
if (ierr /= 0) then
    call exit(1)
end if
```

Example usage, in a physics cap:
```
type(ccpp_t), pointer      :: cdata
real, pointer              :: surf_t(:)
integer                    :: ierr

call c_f_pointer(ptr, cdata)
call ccpp_fields_get(cdata, 'surface_temperature', surf_t, ierr)
if (ierr /= 0) then
    call exit(1)
end if
```

Note, the cap routine must
* Accept only one argument of type `type(c_ptr)`.
* Be marked as `bind(c)`.

## Documentation
The code is documented with [doxygen](www.doxygen.org/).
To generate the documentation you must have [doxygen](www.doxygen.org/)
and [graphviz](http://www.graphviz.org/) installed. The execute:
```
make doc
```

## Code Coverage
The code can be built and run to indicate code coverage. In order to do
this, you must have GNU [gcov](https://gcc.gnu.org/onlinedocs/gcc/Gcov.html)
and [lcov](http://ltp.sourceforge.net/coverage/lcov.php) installed.
To generate the coverage:

1. Make sure you are using the GNU compilers.
2. Configure the build for coverage.
  * `cmake -DCMAKE_BUILD_TYPE=Coverage ..`
3. Build the CCPP.
  * `make`
4. Build the covage report
  * `make coverage`
The coverage report will be in the `coverage` directory within the build.
