#!/usr/bin/python

# Copyright (C) 2006 Peter Poeml / Novell Inc.  All rights reserved.
# This program is free software; it may be used, copied, modified
# and distributed under the terms of the GNU General Public Licence,
# either version 2, or (at your option) any later version.


from core import *
import cmdln
import conf
import oscerr


class Osc(cmdln.Cmdln):
    """usage:
        osc [GLOBALOPTS] SUBCOMMAND [OPTS] [ARGS...]
        osc help SUBCOMMAND
    OpenSUSE build service command-line tool.
    Type 'osc help <subcommand>' for help on a specific subcommand.

    ${command_list}
    ${help_list}
    global ${option_list}
    For additional information, see 
    * http://www.opensuse.org/Build_Service_Tutorial
    * http://www.opensuse.org/Build_Service/CLI
    """
    name = 'osc'
    conf = None


    def __init__(self, *args, **kwargs):
        cmdln.Cmdln.__init__(self, *args, **kwargs)
        cmdln.Cmdln.do_help.aliases.append('h')


    def get_optparser(self):
        """this is the parser for "global" options (not specific to subcommand)"""

        optparser = cmdln.CmdlnOptionParser(self, version=get_osc_version())
        optparser.add_option('--debugger', action='store_true',
                      help='jump into the debugger before executing anything')
        optparser.add_option('--post-mortem', action='store_true',
                      help='jump into the debugger in case of errors')
        optparser.add_option('-t', '--traceback', action='store_true',
                      help='print call trace in case of errors')
        optparser.add_option('-H', '--http-debug', action='store_true',
                      help='debug HTTP traffic')
        optparser.add_option('-d', '--debug', action='store_true',
                      help='print info useful for debugging')
        optparser.add_option('-A', '--apisrv', dest='apisrv',
                      metavar='URL',
                      help='specify URL to access API server at')
        optparser.add_option('-c', '--config', dest='conffile',
                      metavar='FILE',
                      help='specify alternate configuration file')
        return optparser


    def postoptparse(self):
        """merge commandline options into the config"""
        try:
            conf.get_config(override_conffile = self.options.conffile,
                            override_apisrv = self.options.apisrv,
                            override_debug = self.options.debug,
                            override_http_debug = self.options.http_debug,
                            override_traceback = self.options.traceback,
                            override_post_mortem = self.options.post_mortem)
        except oscerr.NoConfigfile, e:
            print >>sys.stderr, e.msg
            print >>sys.stderr, 'Creating osc configuration file %s ...' % e.file
            import getpass
            config = {}
            config['user'] = raw_input('Username: ')
            config['pass'] = getpass.getpass()

            if conf.write_config(e.file, config):
                print >>sys.stderr, 'done'
                conf.get_config(override_conffile = self.options.conffile,
                                override_apisrv = self.options.apisrv,
                                override_debug = self.options.debug,
                                override_http_debug = self.options.http_debug,
                                override_traceback = self.options.traceback,
                                override_post_mortem = self.options.post_mortem)
            else:
                raise NoConfigfile(e.file, 'Unable to create osc\'s configuration file \
                                                 \'%s\'' % e.file)
        self.conf = conf


    def get_cmd_help(self, cmdname):
        doc = self._get_cmd_handler(cmdname).__doc__
        doc = self._help_reindent(doc)
        doc = self._help_preprocess(doc, cmdname)
        doc = doc.rstrip() + '\n' # trim down trailing space
        return self._str(doc)


    def do_init(self, subcmd, opts, project, package):
        """${cmd_name}: Initialize a directory as working copy 

        Initialize a directory to be a working copy of an
        existing buildservice package. 
        
        (This is the same as checking out a
        package and then copying sources into the directory. It does NOT create
        a new package. To create a package, use 'osc meta', then 'osc init'.)

        usage: 
            osc init PRJ PAC
        ${cmd_option_list}
        """

        init_package_dir(conf.config['apiurl'], project, package, os.path.curdir)
        print 'Initializing %s (Project: %s, Package: %s)' % (os.curdir, project, package)


    @cmdln.alias('ls')
    @cmdln.option('-a', '--arch', metavar='ARCH',
                        help='specify architecture')
    @cmdln.option('-r', '--repo', metavar='REPO',
                        help='specify repository')
    @cmdln.option('-b', '--binaries', action='store_true',
                        help='list built binaries, instead of sources')
    @cmdln.option('-v', '--verbose', action='store_true',
                        help='print extra information')
    def do_list(self, subcmd, opts, *args):
        """${cmd_name}: List existing content on the server

        This command is used to list sources, or binaries (when used with the
        --binaries option). To use the --binary option, --repo and --arch are
        also required.

        Examples:
           ls                         # list all projects
           ls Apache                  # list packages in a project
           ls -b Apache               # list all binaries of a project
           ls Apache apache2          # list source files of package of a project
           ls -v Apache apache2       # verbosely list source files of package 

        With --verbose, the following fields will be shown for each item:
           MD5 hash of file
           Revision number of the last commit
           Size (in bytes)
           Date and time of the last commit

        ${cmd_usage}
        ${cmd_option_list}
        """

        args = slash_split(args)

        if len(args) == 1:
            project = args[0]
        elif len(args) == 2:
            project = args[0]
            package = args[1]

        if opts.binaries and (not opts.repo or not opts.arch):
            raise oscerr.WrongOptions('Sorry, -r <repo> -a <arch> missing\n'
                     'You can list repositories with: \'osc platforms <project>\'')

        # list binaries
        if opts.binaries:
            if not args:
                raise oscerr.WrongArgs('There are no binaries to list above project level.')

            elif len(args) == 1:
                #if opts.verbose:
                #    sys.exit('The verbose option is not implemented for projects.')
                r = get_binarylist(conf.config['apiurl'], project, opts.repo, opts.arch)
                print '\n'.join(r)

            elif len(args) == 2:
                r = get_binarylist(conf.config['apiurl'], project, opts.repo, opts.arch, package=package)
                print '\n'.join(r)

        # list sources
        elif not opts.binaries:
            if not args:
                print '\n'.join(meta_get_project_list(conf.config['apiurl']))

            elif len(args) == 1:
                if opts.verbose:
                    raise oscerr.WrongOptions('Sorry, the --verbose option is not implemented for projects.')

                print '\n'.join(meta_get_packagelist(conf.config['apiurl'], project))

            elif len(args) == 2:
                l = meta_get_filelist(conf.config['apiurl'], 
                                      project, 
                                      package,
                                      verbose=opts.verbose)
                if opts.verbose:
                    for i in l:
                        print '%s %7d %9d %s %s' \
                            % (i.md5, i.rev, i.size, shorttime(i.mtime), i.name)
                else:
                    print '\n'.join(l)


    @cmdln.option('-F', '--file', metavar='FILE',
                        help='read metadata from FILE, instead of opening an editor. '
                        '\'-\' denotes standard input. ')
    @cmdln.option('-e', '--edit', action='store_true',
                        help='edit metadata')
    @cmdln.option('--delete', action='store_true',
                        help='delete a pattern file')
    def do_meta(self, subcmd, opts, *args):
        """${cmd_name}: Show meta information, or edit it

        Show or edit build service metadata of type <prj|pkg|prjconf|user|pattern>.

        This command displays metadata on buildservice objects like projects,
        packages, or users. The type of metadata is specified by the word after
        "meta", like e.g. "meta prj".

        prj denotes metadata of a buildservice project.
        prjconf denotes the (build) configuration of a project.
        pkg denotes metadata of a buildservice package.
        user denotes the metadata of a user.
        pattern denotes installation patterns defined for a project.

        To list patterns, use 'osc meta pattern PRJ'. An additional argument
        will be the pattern file to view or edit.

        With the --edit switch, the metadata can be edited. Per default, osc
        opens the program specified by the environmental variable EDITOR with a
        temporary file. Alternatively, content to be saved can be supplied via
        the --file switch. If the argument is '-', input is taken from stdin:
        osc meta prjconf home:poeml | sed ... | osc meta prjconf home:poeml -F -

        When trying to edit a non-existing resource, it is created implicitely.


        Examples:
            osc meta prj PRJ
            osc meta pkg PRJ PKG
            osc meta pkg PRJ PKG -e

        Usage:
            osc meta <prj|pkg|prjconf|user|pattern> ARGS...
            osc meta <prj|pkg|prjconf|user|pattern> -e|--edit ARGS...
            osc meta <prj|pkg|prjconf|user|pattern> -F|--file ARGS...
            osc meta pattern --delete PRJ PATTERN
        ${cmd_option_list}
        """

        args = slash_split(args)

        if not args or args[0] not in metatypes.keys():
            raise oscerr.WrongArgs('Unknown meta type. Choose one of %s.' \
                                               % ', '.join(metatypes))

        cmd = args[0]
        del args[0]

        if cmd in ['pkg']:
            min_args, max_args = 2, 2
        elif cmd in ['pattern']:
            min_args, max_args = 1, 2
        else:
            min_args, max_args = 1, 1
        if len(args) < min_args:
            raise oscerr.WrongArgs('Too few arguments.')
        if len(args) > max_args:
            raise oscerr.WrongArgs('Too many arguments.')

        # specific arguments
        if cmd == 'prj':
            project = args[0]
        elif cmd == 'pkg':
            project, package = args[0:2]
        elif cmd == 'prjconf':
            project = args[0]
        elif cmd == 'user':
            user = args[0]
        elif cmd == 'pattern':
            project = args[0]
            if len(args) > 1:
                pattern = args[1]
            else:
                pattern = None
                # enforce pattern argument if needed
                if opts.edit or opts.file:
                    raise oscerr.WrongArgs('A pattern file argument is required.')

        # show 
        if not opts.edit and not opts.file and not opts.delete:
            if cmd == 'prj':
                sys.stdout.write(''.join(show_project_meta(conf.config['apiurl'], project)))
            elif cmd == 'pkg':
                sys.stdout.write(''.join(show_package_meta(conf.config['apiurl'], project, package)))
            elif cmd == 'prjconf':
                sys.stdout.write(''.join(show_project_conf(conf.config['apiurl'], project)))
            elif cmd == 'user':
                r = get_user_meta(conf.config['apiurl'], user)
                if r:
                    sys.stdout.write(''.join(r))
            elif cmd == 'pattern':
                if pattern:
                    r = show_pattern_meta(conf.config['apiurl'], project, pattern)
                    if r:
                        sys.stdout.write(''.join(r))
                else:
                    r = show_pattern_metalist(conf.config['apiurl'], project)
                    if r:
                        sys.stdout.write('\n'.join(r) + '\n')

        # edit
        if opts.edit and not opts.file:
            if cmd == 'prj':
                edit_meta(metatype='prj', 
                          edit=True,
                          path_args=quote_plus(project),
                          template_args=({
                                  'name': project,
                                  'user': conf.config['user']}))
            elif cmd == 'pkg':
                edit_meta(metatype='pkg', 
                          edit=True,
                          path_args=(quote_plus(project), quote_plus(package)),
                          template_args=({
                                  'name': package,
                                  'user': conf.config['user']}))
            elif cmd == 'prjconf':
                edit_meta(metatype='prjconf', 
                          edit=True,
                          path_args=quote_plus(project),
                          template_args=None)
            elif cmd == 'user':
                edit_meta(metatype='user', 
                          edit=True,
                          path_args=(quote_plus(user)),
                          template_args=({'user': user}))
            elif cmd == 'pattern':
                edit_meta(metatype='pattern', 
                          edit=True,
                          path_args=(project, pattern),
                          template_args=None)

        # upload file
        if opts.file:

            if opts.file == '-':
                f = sys.stdin.read()
            else:
                try:
                    f = open(opts.file).read()
                except:
                    sys.exit('could not open file \'%s\'.' % opts.file)

            if cmd == 'prj':
                edit_meta(metatype='prj', 
                          data=f,
                          edit=opts.edit,
                          path_args=quote_plus(project))
            elif cmd == 'pkg':
                edit_meta(metatype='pkg', 
                          data=f,
                          edit=opts.edit,
                          path_args=(quote_plus(project), quote_plus(package)))
            elif cmd == 'prjconf':
                edit_meta(metatype='prjconf', 
                          data=f,
                          edit=opts.edit,
                          path_args=quote_plus(project))
            elif cmd == 'user':
                edit_meta(metatype='user', 
                          data=f,
                          edit=opts.edit,
                          path_args=(quote_plus(user)))
            elif cmd == 'pattern':
                edit_meta(metatype='pattern', 
                          data=f,
                          edit=opts.edit,
                          path_args=(project, pattern))


        # delete
        if opts.delete:
            path = metatypes[cmd]['path']
            if cmd == 'pattern':
                path = path % (project, pattern)
                u = makeurl(conf.config['apiurl'], [path])
                http_DELETE(u)
            else:
                sys.exit('The --delete switch is only for pattern metadata.')



    @cmdln.option('-d', '--diff', action='store_true',
                  help='generate a diff')
    @cmdln.option('-m', '--message', metavar='TEXT',
                  help='specify message TEXT')
    @cmdln.option('-r', '--revision', metavar='REV',
                  help='for "create", specify a certain source revision ID (the md5 sum)')
    def do_submitreq(self, subcmd, opts, *args):
        """${cmd_name}: Handle requests to submit a package into another project

        For "create", the DESTPAC name is optional; the source packages' name
        will be used if DESTPAC is omitted.
        With --message, a message can be attached.
        With --revision, a revision MD5 of a package can be specified which is
        to be submitted. The default is to request submission of the currently
        checked in revision.

        "list" lists open requests attached to a project or package.

        "show" will show the request itself, and generate a diff for review, if
        used with the --diff option.

        "decline" will change the request state to "declined" and append a
        message that you specify with the --message option.

        "accept" will change the request state to "accepted" and will trigger
        the actual submit process. That would normally be a server-side copy of
        the source package to the target package.


        usage:
            osc submitreq create [-m TEXT] SOURCEPRJ SOURCEPKG DESTPRJ [DESTPKG]
            osc submitreq list PRJ [PKG]
            osc submitreq show [-d] ID
            osc submitreq decline [-m TEXT] ID
            osc submitreq accept [-m TEXT] ID
        ${cmd_option_list}
        """

        args = slash_split(args)

        cmds = ['create', 'list', 'show', 'decline', 'accept']
        if not args or args[0] not in cmds:
            raise oscerr.WrongArgs('Unknown submitreq action. Choose one of %s.' \
                                               % ', '.join(cmds))

        cmd = args[0]
        del args[0]

        if cmd in ['create']:
            min_args, max_args = 3, 4
        elif cmd in ['list']:
            min_args, max_args = 1, 2
        else:
            min_args, max_args = 1, 1
        if len(args) < min_args:
            raise oscerr.WrongArgs('Too few arguments.')
        if len(args) > max_args:
            raise oscerr.WrongArgs('Too many arguments.')

        # collect specific arguments
        if cmd == 'create':
            src_project, src_package, dst_project = args[0:3]
            if len(args) > 3:
                dst_package = args[3]
            else:
                dst_package = src_package

        elif cmd == 'list':
            project = args[0]
            if len(args) > 1:
                package = args[1]
            else:
                package = None
        elif cmd in ['show', 'decline', 'accept']:
            reqid = args[0]


        # create
        if cmd == 'create':
            result = create_submit_request(conf.config['apiurl'], 
                                          src_project, src_package,
                                          dst_project, dst_package,
                                          opts.message, orev=opts.revision)
            print 'created request id', result


        # list
        elif cmd == 'list':
            results = get_submit_request_list(conf.config['apiurl'], 
                                             project, package)
            for result in results:
                print result.list_view()

        # show
        elif cmd == 'show':
            r = get_submit_request(conf.config['apiurl'], reqid)
            print r
            # fixme: will inevitably fail if the given target doesn't exist
            if opts.diff:
                try:
                    print pretty_diff(conf.config['apiurl'],
                                      r.dst_project, r.dst_package, None,
                                      r.src_project, r.src_package, r.src_md5)
                except urllib2.HTTPError, e:
                    e.osc_msg = 'Diff not possible'
                    raise


        # decline
        elif cmd == 'decline':
            r = change_submit_request_state(conf.config['apiurl'], 
                    reqid, 'declined', opts.message or '')
            print r

        # accept
        elif cmd == 'accept':
            r = change_submit_request_state(conf.config['apiurl'], 
                    reqid, 'accepted', opts.message or '')
            print r


    # editmeta and its aliases are all depracated
    @cmdln.alias("editprj")
    @cmdln.alias("createprj")
    @cmdln.alias("editpac")
    @cmdln.alias("createpac")
    @cmdln.alias("edituser")
    @cmdln.alias("usermeta")
    def do_editmeta(self, subcmd, opts, *args):
        """${cmd_name}: 
        
        Obsolete command to edit metadata. Use 'meta' now.

        See the help output of 'meta'.

        """

        print >>sys.stderr, 'This command is obsolete. Use \'osc meta <metatype> ...\'.'
        print >>sys.stderr, 'See \'osc help meta\'.'
        #self.do_help([None, 'meta'])
        return 2


    def do_linkpac(self, subcmd, opts, *args):
        """${cmd_name}: "Link" a package to another package
        
        A linked package is a clone of another package, but plus local
        modifications. It can be cross-project.

        The DESTPAC name is optional; the source packages' name will be used if
        DESTPAC is omitted.

        Afterwards, you will want to 'checkout DESTPRJ DESTPAC'.

        To add a patch, add the patch as file and add it to the _link file.
        You can also specify text which will be inserted at the top of the spec file.

        See the examples in the _link file.

        usage: 
            osc linkpac SOURCEPRJ SOURCEPAC DESTPRJ [DESTPAC]
        ${cmd_option_list}
        """

        args = slash_split(args)

        if not args or len(args) < 3:
            raise oscerr.WrongArgs('Incorrect number of arguments.\n\n' \
                  + self.get_cmd_help('linkpac'))

        src_project = args[0]
        src_package = args[1]
        dst_project = args[2]
        if len(args) > 3:
            dst_package = args[3]
        else:
            dst_package = src_package

        if src_project == dst_project and src_package == dst_package:
            print >>sys.stderr, 'Error: source and destination are the same.'
            return 1
        link_pac(src_project, src_package, dst_project, dst_package)

    def do_aggregatepac(self, subcmd, opts, *args):
        """${cmd_name}: "Aggregate" a package to another package
        
        The DESTPAC name is optional; the source packages' name will be used if
        DESTPAC is omitted.

        usage: 
            osc aggregatepac SOURCEPRJ SOURCEPAC DESTPRJ [DESTPAC]
        ${cmd_option_list}
        """

        args = slash_split(args)

        if not args or len(args) < 3:
            raise oscerr.WrongArgs('Incorrect number of arguments.\n\n' \
                  + self.get_cmd_help('aggregatepac'))

        src_project = args[0]
        src_package = args[1]
        dst_project = args[2]
        if len(args) > 3:
            dst_package = args[3]
        else:
            dst_package = src_package

        if src_project == dst_project and src_package == dst_package:
            print >>sys.stderr, 'Error: source and destination are the same.'
            return 1
        aggregate_pac(src_project, src_package, dst_project, dst_package)

    @cmdln.option('-c', '--client-side-copy', action='store_true',
                        help='do a (slower) client-side copy')
    @cmdln.option('-k', '--keep-maintainers', action='store_true',
                        help='keep original maintainers. Default is remove all and replace with the one calling the script.')
    @cmdln.option('-t', '--to-apiurl', metavar='URL',
                        help='URL of destination api server. Default is the source api server.')
    def do_copypac(self, subcmd, opts, *args):
        """${cmd_name}: Copy a package

        A way to copy package to somewhere else. 
        
        It can be done across buildservice instances, if the -t option is used.
        In that case, a client-side copy is implied.

        Using --client-side-copy always involves downloading all files, and
        uploading them to the target.

        The DESTPAC name is optional; the source packages' name will be used if
        DESTPAC is omitted.

        usage: 
            osc copypac SOURCEPRJ SOURCEPAC DESTPRJ [DESTPAC]
        ${cmd_option_list}
        """

        args = slash_split(args)

        if not args or len(args) < 3:
            raise oscerr.WrongArgs('Incorrect number of arguments.\n\n' \
                  + self.get_cmd_help('copypac'))

        src_project = args[0]
        src_package = args[1]
        dst_project = args[2]
        if len(args) > 3:
            dst_package = args[3]
        else:
            dst_package = src_package

        src_apiurl = conf.config['apiurl']
        if opts.to_apiurl:
            dst_apiurl = opts.to_apiurl
        else:
            dst_apiurl = src_apiurl

        if src_project == dst_project and \
           src_package == dst_package and \
           src_apiurl == dst_apiurl:
                raise oscerr.WrongArgs('Source and destination are the same.')

        if src_apiurl != dst_apiurl:
            opts.client_side_copy = True

        r = copy_pac(src_apiurl, src_project, src_package, 
                     dst_apiurl, dst_project, dst_package,
                     client_side_copy=opts.client_side_copy,
                     keep_maintainers=opts.keep_maintainers)
        print r


    def do_deletepac(self, subcmd, opts, project, package):
        """${cmd_name}: Delete a package on the repository server

        ${cmd_usage}
        ${cmd_option_list}
        """

        delete_package(conf.config['apiurl'], project, package)


    @cmdln.option('-f', '--force', action='store_true',
                        help='deletes a project and its packages')
    def do_deleteprj(self, subcmd, opts, project):
        """${cmd_name}: Delete a project on the repository server

        As a safety measure, project must be empty (i.e., you need to delete all
        packages first). If you are sure that you want to remove this project and all
        its packages use \'--force\' switch.


        ${cmd_usage}
        ${cmd_option_list}
        """

        if len(meta_get_packagelist(conf.config['apiurl'], project)) >= 1 and not opts.force:
            print >>sys.stderr, 'Project contains packages. It must be empty before deleting it. ' \
                                'If you are sure that you want to remove this project and all its ' \
                                'packages use the \'--force\' switch'
            sys.exit(1)
        else:
            delete_project(conf.config['apiurl'], project)


    @cmdln.option('', '--specfile', metavar='FILE',
                      help='Path to specfile. (if you pass more than working copy this option is ignored)')
    def do_updatepacmetafromspec(self, subcmd, opts, *args):
        """${cmd_name}: Update package meta information from a specfile

        ARG, if specified, is a package working copy.

        ${cmd_usage}
        ${cmd_option_list}
        """

        args = parseargs(args)
        if opts.specfile and (len(args) == 1):
            specfile = opts.specfile
        else:
            specfile = None
        pacs = findpacs(args)
        for p in pacs:
            p.read_meta_from_spec(specfile)
            p.update_package_meta()


    @cmdln.alias('di')
    @cmdln.option('-r', '--revision', metavar='rev1[:rev2]',
                        help='If rev1 is specified it will compare your working copy against '
                             'the revision (rev1) on the server. '
                             'If rev1 and rev2 are specified it will compare rev1 against rev2'
                             '(changes in your working copy are ignored in this case).\n'
                             'NOTE: if more than 1 package is specified --revision will be ignored!')
    def do_diff(self, subcmd, opts, *args):
        """${cmd_name}: Generates a diff

        Generates a diff, comparing local changes against the repository
        server.
        
        ARG, specified, is a filename to include in the diff.

        ${cmd_usage}
        ${cmd_option_list}
        """

        args = parseargs(args)
        pacs = findpacs(args)
        
        rev1, rev2 = parseRevisionOption(opts.revision)
        diff = ''
        for pac in pacs:
            diff += ''.join(make_diff(pac, rev1))
        if len(diff) > 0:
            print diff


    @cmdln.option('--oldprj', metavar='OLDPRJ',
                  help='project to compare against')
    @cmdln.option('--oldpkg', metavar='OLDPKG',
                  help='package to compare against')
    @cmdln.option('-r', '--revision', metavar='N[:M]',
                  help='revision id, where N = old revision and M = new revision')
    def do_rdiff(self, subcmd, opts, new_project, new_package):
        """${cmd_name}: Server-side "pretty" diff of two packages

        If neither OLDPRJ nor OLDPKG are specified, the diff is against the
        last revision, thus showing the latest change.

        Note that this command doesn't reply a "normal" diff which can be
        applied as patch, but a pretty diff, which also compares the content of
        tarballs.


        ${cmd_usage}
        ${cmd_option_list}
        """

        old_revision = None
        new_revision = None
        if opts.revision:
            old_revision, new_revision = parseRevisionOption(opts.revision)

        rdiff = pretty_diff(conf.config['apiurl'],
                            opts.oldprj, opts.oldpkg, old_revision,
                            new_project, new_package, new_revision)

        print rdiff


    def do_repourls(self, subcmd, opts, *args):
        """${cmd_name}: Shows URLs of .repo files 

        Shows URLs on which to access the project .repos files (yum-style
        metadata) on download.opensuse.org.

        ARG, if specified, is a package working copy.

        ${cmd_usage}
        ${cmd_option_list}
        """

        args = parseargs(args)
        pacs = findpacs(args)

        url_tmpl = 'http://download.opensuse.org/repositories/%s/%s/%s.repo'
        for p in pacs:
            platforms = get_platforms_of_project(p.apiurl, p.prjname)
            for platform in platforms:
                print url_tmpl % (p.prjname.replace(':', ':/'), platform, p.prjname)



    @cmdln.option('-r', '--revision', metavar='rev',
                        help='checkout the specified revision. '
                             'NOTE: if you checkout the complete project '
                             'this option is ignored!')
    @cmdln.option('-e', '--expand-link', action='store_true',
                        help='if a package is a link, check out the expanded sources')
    @cmdln.alias('co')
    def do_checkout(self, subcmd, opts, *args):
        """${cmd_name}: Check out content from the repository
        
        Check out content from the repository server, creating a local working
        copy.

        When checking out a single package, the option --revision can be used
        to specify a revions of the package to be checked out.

        When --expand-link is used with source link packages, the expanded
        sources will be checked out. Without this option, the _link file and
        patches will be checked out.
        

        examples:
            osc co Apache                    # entire project
            osc co Apache apache2            # a package
            osc co Apache apache2 foo        # single file -> to current dir

        usage: 
            osc co PROJECT [PACKAGE] [FILE]
        ${cmd_option_list}
        """
        args = slash_split(args)
        project = package = filename = None
        try: 
            project = args[0]
            package = args[1]
            filename = args[2]
        except: 
            pass

        rev, dummy = parseRevisionOption(opts.revision)

        if rev and not checkRevision(project, package, rev):
            print >>sys.stderr, 'Revision \'%s\' does not exist' % rev
            sys.exit(1)

        if filename:
            get_source_file(conf.config['apiurl'], project, package, filename, revision=rev)

        elif package:
            checkout_package(conf.config['apiurl'], project, package, 
                             rev, expand_link=opts.expand_link, prj_dir=project)

        elif project:
            if os.path.exists(project):
                sys.exit('osc: project \'%s\' already exists' % project)

            # check if the project does exist (show_project_meta will throw an exception)
            show_project_meta(conf.config['apiurl'], project)

            init_project_dir(conf.config['apiurl'], project, project)
            print statfrmt('A', project)

            # all packages
            for package in meta_get_packagelist(conf.config['apiurl'], project):
                checkout_package(conf.config['apiurl'], project, package, 
                                 expand_link=opts.expand_link, prj_dir=project)
        else:
            raise oscerr.WrongArgs('Missing argument.\n\n' \
                  + self.get_cmd_help('checkout'))


    @cmdln.option('-v', '--verbose', action='store_true',
                        help='print extra information')
    @cmdln.alias('st')
    def do_status(self, subcmd, opts, *args):
        """${cmd_name}: Show status of files in working copy

        Show the status of files in a local working copy, indicating whether
        files have been changed locally, deleted, added, ...

        The first column in the output specifies the status and is one of the
        following characters:
          ' ' no modifications
          'A' Added
          'C' Conflicted
          'D' Deleted
          'M' Modified
          '?' item is not under version control
          '!' item is missing (removed by non-svn command) or incomplete

        examples:
          osc st
          osc st <directory>
          osc st file1 file2 ...

        usage: 
            osc status [OPTS] [PATH...]
        ${cmd_option_list}
        """

        args = parseargs(args)

        # storage for single Package() objects
        pacpaths = []
        # storage for a project dir ( { prj_instance : [ package objects ] } )
        prjpacs = {}
        for arg in args:
            # when 'status' is run inside a project dir, it should
            # stat all packages existing in the wc
            if is_project_dir(arg):
                prj = Project(arg, False)

                if conf.config['do_package_tracking']:
                    prjpacs[prj] = []
                    for pac in prj.pacs_have:
                        # we cannot create package objects if the dir does not exist
                        if not pac in prj.pacs_broken:
                            prjpacs[prj].append(os.path.join(arg, pac))
                else:
                    pacpaths += [arg + '/' + n for n in prj.pacs_have]
            elif is_package_dir(arg):
                pacpaths.append(arg)
            elif os.path.isfile(arg):
                pacpaths.append(arg)
            else:
                msg = '\'%s\' is neither a project or a package directory' % arg
                raise oscerr.NoWorkingCopy, msg
        lines = []
        # process single packages
        lines = getStatus(findpacs(pacpaths), None, opts.verbose)
        # process project dirs
        for prj, pacs in prjpacs.iteritems():
            lines += getStatus(findpacs(pacs), prj, opts.verbose)
        if lines:
            print '\n'.join(lines)


    def do_add(self, subcmd, opts, *args):
        """${cmd_name}: Mark files to be added upon the next commit

        usage: 
            osc add FILE [FILE...]
        ${cmd_option_list}
        """
        if not args:
            raise oscerr.WrongArgs('Missing argument.\n\n' \
                  + self.get_cmd_help('add'))

        filenames = parseargs(args)
        #print filenames
        addFiles(filenames)

    
    def do_mkpac(self, subcmd, opts, *args):
        """${cmd_name}: Create a new package under version control

        usage:
            osc mkpac new_package
        ${cmd_option_list}
        """
        if not conf.config['do_package_tracking']:
            print >>sys.stderr, "enable \'do_package_tracking\' to use this feature"
            sys.exit(1)

        if len(args) != 1:
            raise oscerr.WrongArgs('Wrong number of arguments.')

        createPackageDir(args[0])


    def do_addremove(self, subcmd, opts, *args):
        """${cmd_name}: Adds new files, removes disappeared files

        Adds all files new in the local copy, and removes all disappeared files.

        ARG, if specified, is a package working copy.

        ${cmd_usage}
        ${cmd_option_list}
        """

        args = parseargs(args)
        pacs = findpacs(args)
        for p in pacs:

            p.todo = p.filenamelist + p.filenamelist_unvers

            for filename in p.todo:
                if os.path.isdir(filename):
                    continue
                # ignore foo.rXX, foo.mine for files which are in 'C' state
                if os.path.splitext(filename)[0] in p.in_conflict:
                    continue
                state = p.status(filename)
                if state == '?':
                    p.addfile(filename)
                    print statfrmt('A', filename)
                elif state == '!':
                    p.put_on_deletelist(filename)
                    p.write_deletelist()
                    os.unlink(os.path.join(p.storedir, filename))
                    print statfrmt('D', filename)



    @cmdln.alias('ci')
    @cmdln.alias('checkin')
    @cmdln.option('-m', '--message', metavar='TEXT',
                  help='specify log message TEXT')
    @cmdln.option('-F', '--file', metavar='FILE',
                  help='read log message from FILE')
    def do_commit(self, subcmd, opts, *args):
        """${cmd_name}: Upload content to the repository server

        Upload content which is changed in your working copy, to the repository
        server.

        examples: 
           osc ci                   # current dir
           osc ci <dir>
           osc ci file1 file2 ...

        ${cmd_usage}
        ${cmd_option_list}
        """
        msg = ''
        if opts.message:
            msg = opts.message
        elif opts.file:
            try:
                msg = open(opts.file).read()
            except:
                sys.exit('could not open file \'%s\'.' % opts.file)

        args = parseargs(args)
        for arg in args:
            if conf.config['do_package_tracking'] and is_project_dir(arg):
                Project(arg).commit(msg=msg)
                args.remove(arg)

        pacs = findpacs(args)
        if conf.config['do_package_tracking'] and len(pacs) > 0:
            prj_paths = {}
            single_paths = []
            files = {}
            # it is possible to commit packages from different projects at the same
            # time: iterate over all pacs and put each pac to the right project in the dict
            for pac in pacs:
                path = os.path.normpath(os.path.join(pac.dir, os.pardir))
                if is_project_dir(path):
                    pac_path = os.path.basename(os.path.normpath(pac.absdir))
                    prj_paths.setdefault(path, []).append(pac_path)
                    files[pac_path] = pac.todo
                else:
                    single_paths.append(pac.dir)
            for prj, packages in prj_paths.iteritems():
                Project(prj).commit(tuple(packages), msg, files)
            for pac in single_paths:
                Package(pac).commit(msg)
        else:
            for p in pacs:
                p.commit(msg)


    @cmdln.option('-r', '--revision', metavar='REV',
                        help='update to specified revision (this option will be ignored '
                             'if you are going to update the complete project or more than '
                             'one package)')
    @cmdln.option('-u', '--unexpand-link', action='store_true',
                        help='if a package is an expanded link, update to the raw _link file')
    @cmdln.option('-e', '--expand-link', action='store_true',
                        help='if a package is a link, update to the expanded sources')
    @cmdln.alias('up')
    def do_update(self, subcmd, opts, *args):
        """${cmd_name}: Update a working copy

        examples: 

        1. osc up
                If the current working directory is a package, update it.
                If the directory is a project directory, update all contained
                packages, AND check out newly added packages.

                To update only checked out packages, without checking out new
                ones, you might want to use "osc up *" from within the project
                dir.

        2. osc up PAC
                Update the packages specified by the path argument(s)

        When --expand-link is used with source link packages, the expanded
        sources will be checked out. Without this option, the _link file and
        patches will be checked out. The option --unexpand-link can be used to
        switch back to the "raw" source with a _link file plus patch(es).

        ${cmd_usage}
        ${cmd_option_list}
        """

        args = parseargs(args)

        for arg in args:

            if is_project_dir(arg):
                prj = Project(arg)

                if conf.config['do_package_tracking']:
                    prj.update(expand_link=opts.expand_link, 
                               unexpand_link=opts.unexpand_link)
                    args.remove(arg)
                else:   
                    # if not tracking package, and 'update' is run inside a project dir, 
                    # it should do the following:
                    # (a) update all packages
                    args += prj.pacs_have
                    # (b) fetch new packages
                    prj.checkout_missing_pacs()
                    args.remove(arg)


        pacs = findpacs(args)

        if (opts.expand_link and opts.unexpand_link) \
            or (opts.expand_link and opts.revision) \
            or (opts.unexpand_link and opts.revision):
            raise oscerr.WrongOptions('Sorry, the options --expand-link, --unexpand-link and ' 
                     '--revision are mutually exclusive.')

        if opts.revision and ( len(args) == 1):
            rev, dummy = parseRevisionOption(opts.revision)
            if not checkRevision(pacs[0].prjname, pacs[0].name, rev, pacs[0].apiurl):
                print >>sys.stderr, 'Revision \'%s\' does not exist' % rev
                sys.exit(1)
        else:
            rev = None

        for p in pacs:
            if len(pacs) > 1:
                print 'Updating %s' % p.name

            if opts.expand_link and p.islink() and not p.isexpanded():
                print 'Expanding to rev', p.linkinfo.xsrcmd5
                rev = p.linkinfo.xsrcmd5
            elif opts.unexpand_link and p.islink() and p.isexpanded():
                print 'Unexpanding to rev', p.linkinfo.lsrcmd5
                rev = p.linkinfo.lsrcmd5
            elif p.islink() and p.isexpanded():
                rev = show_upstream_xsrcmd5(p.apiurl,
                                            p.prjname, p.name)

            p.update(rev)
                   

    @cmdln.option('-f', '--force', action='store_true',
                        help='forces removal of package')
    @cmdln.alias('rm')
    @cmdln.alias('del')
    @cmdln.alias('remove')
    def do_delete(self, subcmd, opts, *args):
        """${cmd_name}: Mark files to be deleted upon the next 'checkin'

        usage: 
            osc rm FILE [FILE...]
        ${cmd_option_list}
        """

        if not args:
            raise oscerr.WrongArgs('Missing argument.\n\n' \
                  + self.get_cmd_help('delete'))

        args = parseargs(args)
        # check if args contains a package which was removed by
        # a non-osc command and mark it with the 'D'-state
        for i in args:
            if not os.path.exists(i):
                prj_dir, pac_dir = getPrjPacPaths(i)
                if is_project_dir(prj_dir):
                    prj = Project(prj_dir, False)
                    if i in prj.pacs_broken:
                        if prj.get_state(i) != 'A':
                            prj.set_state(pac_dir, 'D')
                        else:
                            prj.del_package_node(i)
                        print statfrmt('D', getTransActPath(i))
                        args.remove(i)
                        prj.write_packages()
        pacs = findpacs(args)

        for p in pacs:
            if not p.todo:
                prj_dir, pac_dir = getPrjPacPaths(p.absdir)
                if conf.config['do_package_tracking'] and is_project_dir(prj_dir):
                    prj = Project(prj_dir, False)
                    prj.delPackage(p, opts.force)
            else:
                pathn = getTransActPath(p.dir)
                for filename in p.todo:
                    if filename not in p.filenamelist:
                        sys.exit('\'%s\' is not under version control' % filename)
                    p.put_on_deletelist(filename)
                    p.write_deletelist()
                    p.delete_source_file(filename)
                    print statfrmt('D', os.path.join(pathn, filename))


    def do_resolved(self, subcmd, opts, *args):
        """${cmd_name}: Remove 'conflicted' state on working copy files
        
        If an upstream change can't be merged automatically, a file is put into
        in 'conflicted' ('C') state. Within the file, conflicts are marked with
        special <<<<<<< as well as ======== and >>>>>>> lines.
        
        After manually resolving all conflicting parts, use this command to
        remove the 'conflicted' state.

        Note:  this subcommand does not semantically resolve conflicts or
        remove conflict markers; it merely removes the conflict-related
        artifact files and allows PATH to be committed again.

        usage: 
            osc resolved FILE [FILE...]
        ${cmd_option_list}
        """

        if not args:
            raise oscerr.WrongArgs('Missing argument.\n\n' \
                  + self.get_cmd_help('resolved'))

        args = parseargs(args)
        pacs = findpacs(args)

        for p in pacs:

            for filename in p.todo:
                print 'Resolved conflicted state of "%s"' % filename
                p.clear_from_conflictlist(filename)


    def do_platforms(self, subcmd, opts, *args):
        """${cmd_name}: Shows available platforms
        
        Examples:
        1. osc platforms
                Shows all available platforms/build targets

        2. osc platforms <project>
                Shows the configured platforms/build targets of a project

        ${cmd_usage}
        ${cmd_option_list}
        """

        if args:
            project = args[0]
            print '\n'.join(get_platforms_of_project(conf.config['apiurl'], project))
        else:
            print '\n'.join(get_platforms(conf.config['apiurl']))


    def do_results_meta(self, subcmd, opts, *args):
        """${cmd_name}: Shows raw build results of a package

        Shows the build results of the package in raw XML.

        ARG, if specified, is the working copy of a package.

        ${cmd_usage}
        ${cmd_option_list}
        """

        args = parseargs(args)
        pacs = findpacs(args)

        for pac in pacs:
            print ''.join(show_results_meta(pac.apiurl, pac.prjname, package=pac.name))

                
    def do_results(self, subcmd, opts, *args):
        """${cmd_name}: Shows the build results of a package

        ARG, if specified, is the working copy of a package.

        ${cmd_usage}
        ${cmd_option_list}
        """

        args = parseargs(args)
        pacs = findpacs(args)

        for pac in pacs:
            print '\n'.join(get_results(pac.apiurl, pac.prjname, pac.name))

                
    @cmdln.option('-l', '--legend', action='store_true',
                        help='show the legend')
    @cmdln.option('-c', '--csv', action='store_true',
                        help='csv output')
    def do_prjresults(self, subcmd, opts, *args):
        """${cmd_name}: Shows project-wide build results
        
        Examples:

        1. osc prjresults <dir>
                dir is a project or package directory

        2. osc prjresults
                the project is guessed from the current dir

        ${cmd_usage}
        ${cmd_option_list}
        """

        if args and len(args) > 1:
            print >>sys.stderr, 'getting results for more than one project is not supported'
            return 2
            
        if args:
            wd = args[0]
        else:
            wd = os.curdir

        project = store_read_project(wd)
        apiurl = store_read_apiurl(wd)

        print '\n'.join(get_prj_results(apiurl, project, show_legend=opts.legend, csv=opts.csv))

                
    @cmdln.alias('bl')
    def do_buildlog(self, subcmd, opts, platform, arch):
        """${cmd_name}: Shows the build log of a package

        Shows the log file of the build of a package. Can be used to follow the
        log while it is being written.
        Needs to be called from within a package directory.

        The arguments PLATFORM and ARCH are the first two columns in the 'osc
        results' output.

        ${cmd_usage}
        ${cmd_option_list}
        """

        wd = os.curdir
        package = store_read_package(wd)
        project = store_read_project(wd)
        apiurl = store_read_apiurl(wd)

        print_buildlog(apiurl, project, package, platform, arch)


    @cmdln.alias('rbl')
    def do_remotebuildlog(self, subcmd, opts, *args):
        """${cmd_name}: Shows the build log of a package

        Shows the log file of the build of a package. Can be used to follow the
        log while it is being written.

        usage:
            osc remotebuildlog project package platform arch
            or
            osc remotebuildlog project/package/platform/arch
        ${cmd_option_list}
        """
        args = slash_split(args)
        if len(args) < 4:
            raise oscerr.WrongArgs('Too few arguments.')
        elif len(args) > 4:
            raise oscerr.WrongArgs('Too many arguments.')

        print_buildlog(conf.config['apiurl'], *args)


    @cmdln.option('-x', '--extra-pkgs', metavar='PAC', action='append',
                  help='Add this package when computing the buildinfo')
    def do_buildinfo(self, subcmd, opts, *args):
        """${cmd_name}: Shows the build info

        Shows the build "info" which is used in building a package.
        This command is mostly used internally by the 'build' subcommand.
        It needs to be called from within a package directory.

        The BUILD_DESCR argument is optional. BUILD_DESCR is a local RPM specfile
        or Debian "dsc" file. If specified, it is sent to the server, and the
        buildinfo will be based on it. If the argument is not supplied, the
        buildinfo is derived from the specfile which is currently on the source
        repository server.

        The returned data is XML and contains a list of the packages used in
        building, their source, and the expanded BuildRequires.

        The arguments PLATFORM and ARCH can be taken from first two columns
        of the 'osc repos' output.

        usage: 
            osc buildinfo PLATFORM ARCH [BUILD_DESCR]
        ${cmd_option_list}
        """

        wd = os.curdir
        package = store_read_package(wd)
        project = store_read_project(wd)
        apiurl = store_read_apiurl(wd)

        if args is None or len(args) < 2:
            print 'Valid arguments for this package are:'
            print 
            self.do_repos(None, None)
            print
            raise oscerr.WrongArgs('Missing argument')
            
        platform = args[0]
        arch = args[1]

        # were we given a specfile (third argument)?
        try:
            spec = open(args[2]).read()
        except IndexError:
            spec = None
        except IOError, e:
            print >>sys.stderr, e
            return 1

        print ''.join(get_buildinfo(apiurl, 
                                    project, package, platform, arch, 
                                    specfile=spec, 
                                    addlist=opts.extra_pkgs))


    def do_buildconfig(self, subcmd, opts, platform, arch):
        """${cmd_name}: Shows the build config

        Shows the build configuration which is used in building a package.
        This command is mostly used internally by the 'build' command.
        It needs to be called from inside a package directory.

        The returned data is the project-wide build configuration in a format
        which is directly readable by the build script. It contains RPM macros
        and BuildRequires expansions, for example.

        The arguments PLATFORM and ARCH can be taken first two columns in the
        'osc repos' output.

        ${cmd_usage}
        ${cmd_option_list}
        """

        wd = os.curdir
        package = store_read_package(wd)
        project = store_read_project(wd)
        apiurl = store_read_apiurl(wd)

        print ''.join(get_buildconfig(apiurl, project, package, platform, arch))


    def do_repos(self, subcmd, opts, *args):
        """${cmd_name}: Shows the repositories which are defined for a package or a project

        ARG, if specified, is a package working copy or a project dir.

        examples: 1. osc repos                   # project/package = current dir
                  2. osc repos <packagedir>
                  3. osc repos <projectdir>

        ${cmd_usage}
        ${cmd_option_list}
        """

        args = parseargs(args)

        for arg in args:
            for platform in get_repos_of_project(store_read_apiurl(arg), store_read_project(arg)):
                print platform


    @cmdln.option('--clean', action='store_true',
                  help='Delete old build root before initializing it')
    @cmdln.option('--no-changelog', action='store_true',
                  help='don\'t update the package changelog from a changes file')
    @cmdln.option('--noinit', '--no-init', action='store_true',
                  help='Skip initialization of build root and start with build immediately.')
    @cmdln.option('--no-verify', action='store_true',
                  help='Skip signature verification of packages used for build.')
    @cmdln.option('-p', '--prefer-pkgs', metavar='DIR', action='append',
                  help='Prefer packages from this directory when installing the build-root')
    @cmdln.option('-k', '--keep-pkgs', metavar='DIR', 
                  help='Save built packages into this directory')
    @cmdln.option('-x', '--extra-pkgs', metavar='PAC', action='append',
                  help='Add this package when installing the build-root')
    @cmdln.option('-j', '--jobs', metavar='N',
                  help='Compile with N jobs')
    @cmdln.option('--userootforbuild', action='store_true',
                  help='Run build as root. The default is to build as '
                  'unprivileged user. Note that a line "# norootforbuild" '
                  'in the spec file will invalidate this option.')
    @cmdln.option('', '--local-package', action='store_true',
                  help='build a package which does not exist on the server')
    @cmdln.option('', '--alternative-project', metavar='PROJECT',
                  help='specify the build target project')
    @cmdln.option('-d', '--debuginfo', action='store_true',
                  help='also build debuginfo sub-packages')
    def do_build(self, subcmd, opts, *args):
        """${cmd_name}: Build a package on your local machine

        You need to call the command inside a package directory, which should be a
        buildsystem checkout. (Local modifications are fine.)

        The arguments PLATFORM and ARCH can be taken from first two columns
        of the 'osc repos' output. BUILD_DESCR is either a RPM spec file, or a
        Debian dsc file.

        The command honours packagecachedir and build-root settings in .oscrc,
        if present. You may want to set su-wrapper = 'sudo' in .oscrc, and
        configure sudo with option NOPASSWD for /usr/bin/build.

        If neither --clean nor --noinit is given, build will reuse an existing
        build-root again, removing unneeded packages and add missing ones. This
        is usually the fastest option.

        If the package doesn't exist on the server please use the --local-package
        option.
        If the project of the package doesn't exist on the server please use the
        --alternative-project <alternative-project> option:
        Example:
            osc build [OPTS] --alternative-project openSUSE:10.3 standard i586 BUILD_DESCR

        usage: 
            osc build [OPTS] PLATFORM ARCH BUILD_DESCR

        # Note: 
        # Configuration can be overridden by envvars, e.g.  
        # OSC_SU_WRAPPER overrides the setting of su-wrapper. 
        # OSC_BUILD_ROOT overrides the setting of build-root.
        # OSC_PACKAGECACHEDIR overrides the setting of packagecachedir.

        ${cmd_option_list}
        """

        import osc.build

        if not os.path.exists('/usr/lib/build/debtransform') \
                and not os.path.exists('/usr/lib/lbuild/debtransform'):
            sys.stderr.write('Error: you need build.rpm with version 2007.3.12 or newer.\n')
            sys.stderr.write('See http://download.opensuse.org/repositories/openSUSE:/Tools/\n')
            return 1

        if len(args) == 2:
            raise oscerr.WrongArgs('Missing argument: build description (spec of dsc file)')

        elif len(args) < 2:
            # we are going to raise an error for this, but first look up some helpful details:
            msg= ['You have to choose a repo to build on.']
            msg.append('Possible repositories on this machine are:\n')
            for platform in get_repos_of_project(store_read_apiurl(os.curdir),
                                                 store_read_project(os.curdir)):
                arch = platform.split()[1] # arch
                if arch == osc.build.hostarch or \
                   arch in osc.build.can_also_build.get(osc.build.hostarch, []):
                    msg.append(platform.strip())
            raise oscerr.WrongArgs('Missing argument.\n\n' + '\n'.join(msg))

        elif len(args) > 3:
            raise oscerr.WrongArgs('Too many arguments')

        if opts.prefer_pkgs:
            for d in opts.prefer_pkgs:
                if not os.path.isdir(d):
                    print >> sys.stderr, 'Preferred package location \'%s\' is not a directory' % d
                    return 1

        if opts.keep_pkgs:
            if not os.path.isdir(opts.keep_pkgs):
                print >> sys.stderr, 'Preferred save location \'%s\' is not a directory' % opts.keep_pkgs
                return 1

        return osc.build.main(opts, args)

            

    @cmdln.alias('buildhist')
    def do_buildhistory(self, subcmd, opts, platform, arch):
        """${cmd_name}: Shows the build history of a package

        The arguments PLATFORM and ARCH can be taken from first two columns
        of the 'osc repos' output.

        ${cmd_usage}
        ${cmd_option_list}
        """

        wd = os.curdir
        package = store_read_package(wd)
        project = store_read_project(wd)
        apiurl = store_read_apiurl(wd)

        print '\n'.join(get_buildhistory(apiurl, project, package, platform, arch))


    @cmdln.option('-r', '--revision', metavar='rev',
                        help='show log of the specified revision')
    def do_log(self, subcmd, opts):
        """${cmd_name}: Shows the commit log of a package

        ${cmd_usage}
        ${cmd_option_list}
        """

        wd = os.curdir
        package = store_read_package(wd)
        project = store_read_project(wd)
        apiurl = store_read_apiurl(wd)
        rev, dummy = parseRevisionOption(opts.revision)
        if rev and not checkRevision(project, package, rev, apiurl):
            print >>sys.stderr, 'Revision \'%s\' does not exist' % rev
            sys.exit(1)

        print '\n'.join(get_commitlog(apiurl, project, package, rev))


    @cmdln.option('-f', '--failed', action='store_true',
                  help='rebuild all failed packages')
    def do_rebuildpac(self, subcmd, opts, *args):
        """${cmd_name}: Triggers package rebuilds

        With the optional <repo> and <arch> arguments, the rebuild can be limited
        to a certain repository or architecture.

        Note that it is normally NOT needed to kick off rebuilds like this, because
        they principally happen in a fully automatic way, triggered by source
        check-ins. In particular, the order in which packages are built is handled
        by the build service.

        Note the --failed option, which can be used to rebuild all failed
        packages.

        The arguments PLATFORM and ARCH are as in the first two columns of the
        'osc repos' output.

        usage: 
            osc rebuildpac PROJECT [PACKAGE [PLATFORM [ARCH]]]
        ${cmd_option_list}
        """

        args = slash_split(args)

        if len(args) < 1:
            raise oscerr.WrongArgs('Missing argument.')

        package = repo = arch = code = None
        project = args[0]
        if len(args) > 1:
            package = args[1]
        if len(args) > 2:
            repo = args[2]
        if len(args) > 3:
            arch = args[3]

        if opts.failed:
            code = 'failed'

        print rebuild(conf.config['apiurl'], project, package, repo, arch, code)


    def do_info(self, subcmd, opts, *args):
        """${cmd_name}: Print information about a working copy

        Print information about each ARG (default: '.')
        ARG is a working-copy path.

        ${cmd_usage}
        ${cmd_option_list}
        """

        args = parseargs(args)
        pacs = findpacs(args)


        for p in pacs:
            print p.info()


    @cmdln.option('-a', '--arch', metavar='ARCH',
                        help='Abort builds for a specific architecture')
    @cmdln.option('-r', '--repo', metavar='REPO',
                        help='Abort builds for a specific repository')
    def do_abortbuild(self, subcmd, opts, *args):
        """${cmd_name}: Aborts the build of a certain project/package
        
        With the optional argument <package> you can specify a certain package
        otherwise all builds in the project will be cancelled.
        
        usage: 
            osc abortbuild [OPTS] PROJECT [PACKAGE]
        ${cmd_option_list}
        """

        if len(args) < 1:
            raise oscerr.WrongArgs('Missing <project> argument.')

        if len(args) == 2:
            package = args[1]
        else:
            package = None

        print abortbuild(conf.config['apiurl'], args[0], package, opts.arch, opts.repo)


    @cmdln.option('-a', '--arch', metavar='ARCH',
                        help='Delete all binary packages for a specific architecture')
    @cmdln.option('-r', '--repo', metavar='REPO',
                        help='Delete all binary packages for a specific repository')
    @cmdln.option('--build-disabled', action='store_true',
                        help='Delete all binaries of packages for which the build is disabled')
    @cmdln.option('--build-failed', action='store_true',
                        help='Delete all binaries of packages for which the build failed')
    @cmdln.option('--broken', action='store_true',
                        help='Delete all binaries of packages for which the package source is bad')
    def do_wipebinaries(self, subcmd, opts, *args):
        """${cmd_name}: Delete all binary packages of a certain project/package

        With the optional argument <package> you can specify a certain package
        otherwise all binary packages in the project will be deleted.

        usage: 
            osc wipebinaries [OPTS] PROJECT [PACKAGE]
        ${cmd_option_list}
        """
        
        args = slash_split(args)

        if len(args) < 1:
            raise oscerr.WrongArgs('Missing <project> argument.')
        
        if len(args) == 2:
            package = args[1]
        else:
            package = None

        codes = []
        if opts.build_disabled:
            codes.append('disabled')
        if opts.build_failed:
            codes.append('failed')
        if opts.broken:
            codes.append('broken')

        if len(codes) == 0:
            codes.append(None)

        # make a new request for each code= parameter
        for code in codes:
            print wipebinaries(conf.config['apiurl'], args[0], package, opts.arch, opts.repo, code)


    @cmdln.option('--repos-baseurl', action='store_true',
                        help='show base URLs of download repositories')
    @cmdln.option('-e', '--enable-exact', action='store_true',
                        help='show only exact matches')
    @cmdln.option('--package', action='store_true',
                        help='search for a package')
    @cmdln.option('--project', action='store_true',
                        help='search for a project')
    @cmdln.option('--title', action='store_true',
                        help='search for matches in the \'title\' element')
    @cmdln.option('--description', action='store_true',
                        help='search for matches in the \'description\' element')
    @cmdln.option('-v', '--verbose', action='store_true',
                        help='show more information')
    def do_search(self, subcmd, opts, *args):
        """${cmd_name}: Search for a project and/or package.

        If no option is specified osc will search for projects and
        packages which contains the \'search term\' in their name,
        title or description.

        usage:
            osc search \'search term\' <options>
        ${cmd_option_list}
        """

        if len(args) > 1:
            raise oscerr.WrongArgs('Too many arguments.')
        elif len(args) < 1:
            raise oscerr.WrongArgs('Too few arguments.')

        search_list = []
        search_for = []
        if opts.title:
            search_list.append('title')
        if opts.description:
            search_list.append('description')
        if opts.package:
            search_list.append('@name')
            search_for.append('package')
        if opts.project:
            search_list.append('@name')
            search_for.append('project')

        if not search_list:
            search_list = ['title', 'description', '@name']
        if not search_for:
            search_for = [ 'project', 'package' ]
        for kind in search_for:
            result = search(conf.config['apiurl'], set(search_list), kind, args[0], opts.verbose, opts.enable_exact, opts.repos_baseurl)
            if result:
                if kind == 'package':
                    headline = [ '# Package', '# Project' ]
                else:
                    headline = [ '# Project' ]
                if opts.verbose:
                    headline.append('# Title')
                if opts.repos_baseurl:
                    headline.append('# URL')
                if len(search_for) > 1:
                    print '#' * 68
                print 'matches for \'%s\' in %ss:\n' % (args[0], kind)
                for row in build_table(len(headline), result, headline, 2):
                    print row
            else:
               print 'No matches found for \'%s\' in %ss' % (args[0], kind)


    @cmdln.option('-p', '--project', metavar='project',
                        help='specify a project name')
    @cmdln.option('-n', '--name', metavar='name',
                        help='specify a package name')
    @cmdln.option('-t', '--title', metavar='title',
                        help='set a title')
    @cmdln.option('-d', '--description', metavar='description',
                        help='set the description of the package')
    @cmdln.option('',   '--delete-old-files', action='store_true',
                        help='delete existing files from the server')
    @cmdln.option('-c',   '--commit', action='store_true',
                        help='commit the new files')
    def do_importsrcpkg(self, subcmd, opts, srpm):
        """${cmd_name}: Import a new package from a src.rpm

        A new package dir will be created inside the project dir
        (if no project is specified and the current working dir is a
        project dir the package will be created in this project). If
        the package does not exist on the server it will be created
        too otherwise the meta data of the existing package will be
        updated (<title /> and <description />).
        The src.rpm will be extracted into the package dir. If the
        --disable-commit switch is not used all changes will be
        committed.

        SRPM is the path of the src.rpm in the local filesystem,
        or an URL.

        ${cmd_usage}
        ${cmd_option_list}
        """
        import glob

        if opts.delete_old_files and conf.config['do_package_tracking']:
            # IMHO the --delete-old-files option doesn't really fit into our
            # package tracking strategy
            print >>sys.stderr, '--delete-old-files is not supported anymore'
            print >>sys.stderr, 'when do_package_tracking is enabled'
            sys.exit(1)

        if '://' in srpm:
            print 'trying to fetch', srpm
            import urlgrabber
            urlgrabber.urlgrab(srpm)
            srpm = os.path.basename(srpm)

        srpm = os.path.abspath(srpm)
        if not os.path.isfile(srpm):
            print >>sys.stderr, 'file \'%s\' does not exist' % srpm
            sys.exit(1)

        if opts.project:
            project_dir = opts.project
        else:
            project_dir = os.curdir

        if conf.config['do_package_tracking']:
            project = Project(project_dir)
        else:
            project = store_read_project(project_dir)

        rpm_data = data_from_rpm(srpm, 'Name:', 'Summary:', '%description')
        if rpm_data:
            title, pac, descr = ( v for k, v in rpm_data.iteritems() )
        else:
            title = pac = descr = ''

        if opts.title:
            title = opts.title
        if opts.name:
            pac = opts.name
        if opts.description:
            descr = opts.description
        
        # title and description can be empty
        if not pac:
            print >>sys.stderr, 'please specify a package name with the \'--name\' option. ' \
                                'The automatic detection failed'
            sys.exit(1)

        olddir = os.getcwd()
        if conf.config['do_package_tracking']:
            if createPackageDir(os.path.join(project.dir, pac), project):
                os.chdir(os.path.join(project.dir, pac))
            else:
                sys.exit(1)
        else:
            if not os.path.exists(os.path.join(project_dir, pac)):
                apiurl = store_read_apiurl(project_dir)
                user = conf.get_apiurl_usr(apiurl)
                data = meta_exists(metatype='pkg',
                                   path_args=(quote_plus(project), quote_plus(pac)),
                                   template_args=({
                                       'name': pac,
                                       'user': user}), apiurl=apiurl)
                if data:
                    data = ET.fromstring(''.join(data))
                    data.find('title').text = title
                    data.find('description').text = ''.join(descr)
                    data = ET.tostring(data)
                else:
                    print >>sys.stderr, 'error - cannot get meta data'
                    sys.exit(1)
                edit_meta(metatype='pkg',
                          path_args=(quote_plus(project), quote_plus(pac)),
                          data = data, apiurl=apiurl)
                os.mkdir(os.path.join(project_dir, pac))
                os.chdir(os.path.join(project_dir, pac))
                init_package_dir(apiurl, project, pac, os.path.join(project, pac))
            else:
                print >>sys.stderr, 'error - local package already exists'
                sys.exit(1)

        unpack_srcrpm(srpm, os.getcwd())
        p = Package(os.getcwd())
        if len(p.filenamelist) == 0 and opts.commit:
            print 'Adding files to working copy...'
            addFiles(glob.glob('*'))
            if conf.config['do_package_tracking']:
                os.chdir(olddir)
                project.commit((pac, ))
            else:
                p.update_datastructs()
                p.commit()
        elif opts.commit and opts.delete_old_files:
            for file in p.filenamelist:
                p.delete_remote_source_file(file)
            p.update_local_filesmeta()
            print 'Adding files to working copy...'
            addFiles(glob.glob('*'))
            p.update_datastructs()
            p.commit()
        else:
            print 'No files were committed to the server. Please ' \
                  'commit them manually.'
            print 'Package \'%s\' only imported locally' % pac
            sys.exit(1)

        print 'Package \'%s\' imported successfully' % pac


    @cmdln.option('-m', '--method', default='GET', metavar='HTTP_METHOD',
                        help='specify HTTP method to use (GET|PUT|DELETE|POST)')
    @cmdln.option('-d', '--data', default=None, metavar='STRING',
                        help='specify string data for e.g. POST')
    @cmdln.option('-f', '--file', default=None, metavar='FILE',
                        help='specify filename for e.g. PUT or DELETE')
    @cmdln.option('-a', '--add-header', default=None, metavar='NAME STRING', 
                        nargs=2, action='append', dest='headers',
                        help='add the specified header to the request')
    def do_req(self, subcmd, opts, url):
        """${cmd_name}: Issue an arbitrary request to the API

        Useful for testing.

        URL can be specified either partially (only the path component), or fully
        with URL scheme and hostname ('http://...').

        Note the global -A and -H options (see osc help).

        Examples:
          osc req /source/home:poeml
          osc req -m PUT -f /etc/fstab source/home:poeml/test5/myfstab

        ${cmd_usage}
        ${cmd_option_list}
        """

        if not opts.method in ['GET', 'PUT', 'POST', 'DELETE']:
            sys.exit('unknown method %s' % opts.method)

        if not url.startswith('http'):
            if not url.startswith('/'):
                url = '/' + url
            url = conf.config['apiurl'] + url

        if opts.headers:
            opts.headers = dict(opts.headers)

        r = http_request(opts.method, 
                         url, 
                         data=opts.data, 
                         file=opts.file,
                         headers=opts.headers) 

        out = r.read()
        sys.stdout.write(out)


    @cmdln.option('-e', '--email', action='store_true',
                  help='show email addresses instead of user names')
    @cmdln.option('-v', '--verbose', action='store_true',
                  help='show more information')
    @cmdln.option('-a', '--add', metavar='user',
                  help='add a new maintainer')
    @cmdln.option('-d', '--delete', metavar='user',
                  help='delete a maintainer from a project or package')
    def do_maintainer(self, subcmd, opts, *args):
        """${cmd_name}: Show maintainers of a project/package
    
        To be used like this:
    
            osc maintainer PRJ <options>
        or 
            osc maintainer PRJ PKG <options>
    
        ${cmd_usage}
        ${cmd_option_list}
        """
    
        pac = None
        if len(args) == 1:
            m = show_project_meta(conf.config['apiurl'], args[0])
            prj = args[0]
        elif len(args) == 2:
            m = show_package_meta(conf.config['apiurl'], args[0], args[1])
            prj = args[0]
            pac = args[1]
        else:
            raise oscerr.WrongArgs('I need at least one argument.')
    
        maintainers = []
    
        tree = ET.parse(StringIO(''.join(m)))
        for person in tree.findall('person'):
            maintainers.append(person.get('userid'))
    
        if opts.email:
            emails = []
            for maintainer in maintainers:
                user = get_user_data(conf.config['apiurl'], maintainer, 'email')
                if user != None:
                    emails.append(''.join(user))
            print ', '.join(emails)
        elif opts.verbose:
            userdata = []
            for maintainer in maintainers:
                user = get_user_data(conf.config['apiurl'], maintainer, 'realname', 'login', 'email')
                if user != None:
                    for itm in user:
                        userdata.append(itm)
            for row in build_table(3, userdata, ['realname', 'userid', 'email\n']):
                print row
        elif opts.add:
            addMaintainer(conf.config['apiurl'], prj, pac, opts.add)
        elif opts.delete:
            delMaintainer(conf.config['apiurl'], prj, pac, opts.delete)
        else:
            print ', '.join(maintainers)


    @cmdln.option('-r', '--revision', metavar='rev',
                  help='print out the specified revision')
    def do_cat(self, subcmd, opts, *args):
        """${cmd_name}: Output the content of a file to standard output

        Examples:
            osc cat project package file
            osc cat project/package/file

        ${cmd_usage}
        ${cmd_option_list}
        """

        args = slash_split(args)
        if len(args) != 3:
            raise oscerr.WrongArgs('Wrong number of arguments.')
        rev, dummy = parseRevisionOption(opts.revision)

        import tempfile
        (fd, filename) = tempfile.mkstemp(prefix = 'osc_%s.' % args[2], dir = '/tmp')

        get_source_file(conf.config['apiurl'], args[0], args[1], args[2],
                        targetfilename=filename, revision=rev)

        if binary_file(filename):
            print >>sys.stderr, 'error - cannot display binary file \'%s\'' % args[2]
        else:
            for line in open(filename):
                print line.rstrip('\n')

        try:
            os.unlink(filename)
        except:
            pass
# fini!
###############################################################################
        
    # load subcommands plugged-in locally
    plugin_dirs = ['/var/lib/osc-plugins', os.path.expanduser('~/.osc-plugins')]
    for plugin_dir in plugin_dirs:
        if os.path.isdir(plugin_dir):
            for extfile in os.listdir(plugin_dir):
                if not extfile.endswith('.py'):
                    continue
                exec open(os.path.join(plugin_dir, extfile))


