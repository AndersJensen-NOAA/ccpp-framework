!>
!! @brief Physics infrastructure module.
!
module ccpp_phy_infra

   use, intrinsic :: iso_c_binding
   use            :: kinds,                                            &
                     only: i_sp, r_dp
   use            :: ccpp_types,                                       &
                     only: STR_LEN, suite_t, ipd_t, subcycle_t,        &
                           aip_t, field_t
   use            :: ccpp_errors,                                      &
                     only: ccpp_error, ccpp_warn
   use            :: ccpp_strings,                                     &
                     only: ccpp_fstr, ccpp_cstr
   use            :: ccpp_xml
   implicit none

   private
   public :: ccpp_phy_init

   !>
   !! @brief Suite XML tags.
   !!
   !! @details These suite xml tags must match the elements and attributes
   !!          of the suite.xsd.
   !
   character(len=*), parameter :: XML_ELE_SUITE    = "suite"
   character(len=*), parameter :: XML_ELE_IPD      = "ipd"
   character(len=*), parameter :: XML_ELE_SUBCYCLE = "subcycle"
   character(len=*), parameter :: XML_ELE_SCHEME   = "scheme"
   character(len=*), parameter :: XML_ATT_NAME     = "name"
   character(len=*), parameter :: XML_ATT_PART     = "part"
   character(len=*), parameter :: XML_ATT_LOOP     = "loop"

   contains

   !>
   !! Physics infrastructure initialization subroutine.
   !!
   !! @param[in]    filename The file name of the XML scheme file to load.
   !! @param[inout] suite    The suite_t type to initalize from the scheme
   !!                        XML file.
   !
   subroutine ccpp_phy_init(filename, suite, ierr)
        implicit none

        character(len=*),       intent(in)    :: filename
        type(suite_t),          intent(inout) :: suite
        integer,                intent(  out) :: ierr

        logical                               :: is_subcycle
        integer                               :: i
        integer                               :: j
        integer                               :: k
        integer                               :: n
        integer                               :: max_num_schemes_per_ipd_call
        integer                               :: num_schemes_this_ipd_call
        type(c_ptr)                           :: xml
        type(c_ptr)                           :: root
        type(c_ptr)                           :: ipd
        type(c_ptr)                           :: subcycle
        type(c_ptr)                           :: scheme
        type(c_ptr), target                   :: tmp
        character(kind=c_char), target        :: stmp(STR_LEN)
        character(len=:), parameter           :: err_msg =             &
            'Please validate the suite xml file: '

        ierr = 0
        max_num_schemes_per_ipd_call = 0

        ! Load the xml document.
        ierr = ccpp_xml_load(ccpp_cstr(filename), xml, root)
        if (ierr /= 0) then
            call ccpp_error('Unable to load suite from: ' // trim(filename))
            return
        end if

        ! Get the suite name
        ierr = ccpp_xml_ele_att(root, ccpp_cstr(XML_ATT_NAME), tmp)
        if (ierr /= 0) then
            call ccpp_error('Unable retrieving suite name')
            call ccpp_error(err_msg // trim(filename))
            return
        end if

        suite%name = ccpp_fstr(tmp)

        ! Count the number of IPDs
        ierr = ccpp_xml_ele_count(root, ccpp_cstr(XML_ELE_IPD), suite%ipds_max)
        if (ierr /= 0) then
            call ccpp_error('Unable count the number of ipds')
            call ccpp_error(err_msg // trim(filename))
            return
        end if

        allocate(suite%ipds(suite%ipds_max), stat=ierr)
        if (ierr /= 0) then
            call ccpp_error('Unable to allocate ipds')
            return
        end if

        ! Find the first IPD
        ierr = ccpp_xml_ele_find(root, ccpp_cstr(XML_ELE_IPD), ipd)
        if (ierr /= 0) then
            call ccpp_error('Unable to find first ipd')
            call ccpp_error(err_msg // trim(filename))
            return
        end if

        ! Loop over all IPDs
        do i=1, suite%ipds_max

            ! Get the part number
            ierr = ccpp_xml_ele_att(ipd, ccpp_cstr(XML_ATT_PART), tmp)

            ! Optional if only 1 IPD
            if (ierr /= 0 .and. suite%ipds_max == 1) then
                call ccpp_warn('Unable to find attribute: ' // XML_ATT_PART &
                               // ' assuming 1')
                suite%ipds(i)%part = 1
            else if (ierr /= 0 .and. suite%ipds_max > 1) then
                call ccpp_error('Unable to find attribute: ' // XML_ATT_PART)
                call ccpp_error(err_msg // trim(filename))
                return
            else
                stmp = ccpp_fstr(tmp)
                read(stmp,*,iostat=ierr) suite%ipds(i)%part
                if (ierr /= 0) then
                    call ccpp_error('Unable to convert ipd attribute "' // &
                                    XML_ATT_PART // '" to an integer')
                    return
                end if
            end if

            ! Count the number of subcycles in this IPD
            ierr = ccpp_xml_ele_count(ipd, ccpp_cstr(XML_ELE_SUBCYCLE), n)
            if (ierr /= 0) then
                call ccpp_error('Unable to count elements: ' // XML_ELE_SUBCYCLE)
                call ccpp_error(err_msg // trim(filename))
                return
            end if

            ! subcycles are optional, but we need to store the scheme under them
            if (n == 0) then
                n = 1
                is_subcycle = .false.
                subcycle = ipd
            else
                is_subcycle = .true.
            end if

            suite%ipds(i)%subcycles_max = n
            allocate(suite%ipds(i)%subcycles(n), stat=ierr)
            if (ierr /= 0) then
                call ccpp_error('Unable to allocate subcycles')
                return
            end if

            ! Count the number of scheme calls for this IPD
            num_schemes_this_ipd_call = 0

            ! Find the first subcycle
            if (is_subcycle .eqv. .true.) then
                ierr = ccpp_xml_ele_find(ipd, ccpp_cstr(XML_ELE_SUBCYCLE), subcycle)
                if (ierr /= 0) then
                    call ccpp_error('Unable to locate element: ' // XML_ELE_SUBCYCLE)
                    call ccpp_error(err_msg // trim(filename))
                    return
                end if
            end if

            ! Loop over all subcycles
            do j=1, suite%ipds(i)%subcycles_max

                ! Get the (optional) subcycle loop number
                ierr = ccpp_xml_ele_att(subcycle, ccpp_cstr(XML_ATT_LOOP), tmp)
                if (ierr /= 0 .and. suite%ipds(i)%subcycles_max == 1) then
                    call ccpp_warn('Unable to locate attribute: ' // & 
                                   XML_ATT_LOOP // ' assuming 1')
                    suite%ipds(i)%subcycles(j)%loop = 1
                else if (ierr /= 0 .and. suite%ipds(i)%subcycles_max > 1) then
                    call ccpp_error('Unable to find attribute: ' // XML_ATT_LOOP)
                    call ccpp_error(err_msg // trim(filename))
                    return
                else
                    stmp = ccpp_fstr(tmp)
                    read(stmp,*,iostat=ierr) suite%ipds(i)%subcycles(j)%loop
                    if (ierr /= 0) then
                        call ccpp_error('Unable to convert subcycle attribute ' &
                                        // XML_ATT_LOOP // ' to an integer')
                        return
                    end if
                end if

                ! Count the number of schemes
                ierr = ccpp_xml_ele_count(subcycle, ccpp_cstr(XML_ELE_SCHEME), n)
                if (ierr /= 0) then
                    call ccpp_error('Unable to locate element: ' // XML_ELE_SUBCYCLE)
                    call ccpp_error(err_msg // trim(filename))
                    return
                end if

                suite%ipds(i)%subcycles(j)%schemes_max = n
                allocate(suite%ipds(i)%subcycles(j)%schemes(n), stat=ierr)
                num_schemes_this_ipd_call = n
                max_num_schemes_per_ipd_call = MAX ( max_num_schemes_per_ipd_call , num_schemes_this_ipd_call )

                ! Find the first scheme
                ierr = ccpp_xml_ele_find(subcycle, ccpp_cstr(XML_ELE_SCHEME), &
                                         scheme)

                ! Loop over all scheme
                do k=1, suite%ipds(i)%subcycles(j)%schemes_max
                    ierr = ccpp_xml_ele_contents(scheme, tmp)
                    suite%ipds(i)%subcycles(j)%schemes(k) = ccpp_fstr(tmp)
                    ! Find the next scheme
                    ierr = ccpp_xml_ele_next(scheme, ccpp_cstr(XML_ELE_SCHEME), &
                                             scheme)
                end do

                ! Find the next subcycle
                ierr = ccpp_xml_ele_next(ipd, ccpp_cstr(XML_ELE_SUBCYCLE), &
                                         subcycle)
            end do
            ! Find the next IPD
            ierr = ccpp_xml_ele_next(ipd, ccpp_cstr(XML_ELE_IPD), ipd)
        end do

        ! Save max number of schemes that appear in any single IPD call
        !suite%total_schemes_max = max_num_schemes_per_ipd_call

        write(*, '(A, A)') 'Suite name: ', trim(suite%name)
        write(*, '(A, I4)') 'IPDs: ', suite%ipds_max

        do i=1, suite%ipds_max
            write(*, '(A, I4, A, I4)') 'IPD: ', i, ' part: ', suite%ipds(i)%part
            write(*, '(A, I4)') 'subcycles: ',  suite%ipds(i)%subcycles_max
            do j=1, suite%ipds(i)%subcycles_max
                write(*, '(A, I4, A, I4)') 'subcycle: ', j, ' loop: ', suite%ipds(i)%subcycles(j)%loop
                write(*, '(A, I4)') 'schemes: ', suite%ipds(i)%subcycles(j)%schemes_max
                do k=1, suite%ipds(i)%subcycles(j)%schemes_max
                    write(*, '(A, A)') 'scheme: ', trim(suite%ipds(i)%subcycles(j)%schemes(k))
                end do
            end do
        end do

        ierr = ccpp_xml_unload(xml)

   end subroutine ccpp_phy_init

end module ccpp_phy_infra
