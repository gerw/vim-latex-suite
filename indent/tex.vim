" Vim indent file
"
" Options: {{{
"
" The options are mostly compatible with the indent/tex.vim distributed by
" vim.
" Here, we have one new option: g:tex_indent_ifelsefi
"
" To set the following options, add a line like
"   let g:tex_indent_items = 1
" to your ~/ftplugin/tex.vim.
"
"
" * g:tex_indent_brace = 1
"
"   If this variable is unset or non-zero, it will use smartindent-like style
"   for "{}", "[]" and "()".
"
"
" * g:tex_indent_items = 1
"
"   If this variable is set, item-environments are indented like Emacs does
"   it, i.e., continuation lines are indented with a shiftwidth.
"
"              set                                unset
"   ----------------------------------------------------------------
"       \begin{itemize}                      \begin{itemize}
"         \item blablabla                      \item blablabla
"           bla bla bla                        bla bla bla
"         \item blablabla                      \item blablabla
"           bla bla bla                        bla bla bla
"       \end{itemize}                        \end{itemize}
"
"
" * g:tex_items = '\\bibitem\|\\item'
"
"   A list of tokens to be considered as commands for the beginning of an item
"   command. The tokens should be separated with '\|'. The initial '\' should
"   be escaped.
"
"
" * g:tex_itemize_env = 'itemize\|description\|enumerate\|thebibliography'.
"
"   A list of environment names, separated with '\|', where the items (item
"   commands matching g:tex_items) may appear.
"
"
" * g:tex_noindent_env = 'document\|verbatim\|comment\|lstlisting'
"
"   A list of environment names. separated with '\|', where no indentation is
"   required.
"
"
" * g:tex_indent_ifelsefi = 1
"
"   If this is set to one, we try to indent something like
"   \ifnum...
"     bar
"   \else
"     foo
"   \fi
"   correctly. This is quite tough, since there are commands like
"   \ifthenelse{condition}{then}{else}, which uses braces instead of \else and
"   \fi. Our heuristic: only add indentation, if \if... is not followed by a
"   '{', (and only if \if,\else,\or,\fi occur at the beginning of the line).
"
" }}}

if exists("b:did_indent")
	finish
endif
let b:did_indent = 1

" Check whether the options exist and assign default values
if !exists("g:tex_indent_brace")
	let g:tex_indent_brace = 1
endif
if !exists("g:tex_indent_items")
	let g:tex_indent_items = 1
endif
if !exists('g:tex_items')
	let g:tex_items = '\\bibitem\|\\item'
endif
if !exists("g:tex_itemize_env")
	let g:tex_itemize_env = 'itemize\|description\|enumerate\|thebibliography'
endif
if !exists("g:tex_noindent_env")
	let g:tex_noindent_env = 'document\|verbatim\|comment\|lstlisting'
endif
if !exists("g:tex_indent_ifelsefi")
	let g:tex_indent_ifelsefi = 1
endif

setlocal autoindent
setlocal nosmartindent
setlocal indentexpr=Tex_CalcIdent()
setlocal indentkeys+=},],.,)

" Add indentkeys depending on options
if g:tex_indent_items
	exec 'setlocal indentkeys+=' . substitute(g:tex_items, '^\|\(\\|\)', ',0=', 'g')
endif
if g:tex_indent_ifelsefi
	setlocal indentkeys+=0=\\else,0=\\or,0=\\fi
endif

" Function DeepestNesting:
" This function computes the deepest/smallest nesting on the current line. We
" start with 0, each match of openregexp increases nesting and each match of
" closeregexp decreases nesting.
" The return value is the deepest indentation of the current line and the
" additional indentation which should be used for the next line.
" Parameters:
"   line              This string should be indented
"   openregexp        Causes 1 indentation more
"   closeregexp       Causes 1 indentation less
"   openextraregexp   Causes 2 indentations more
"   closeextraregexp  Causes 2 indentations less
"   hangingregexp     Only this line has 1 indentation less
"
" All the regexps should be able to be combined via \|, preferably single
" atoms (enclose them in '\%(', '\)'!)
function! s:DeepestNesting(line, openregexp, closeregexp, openextraregexp, closeextraregexp, hangingregexp)
	let indent = 0
	let pos = 0

	let deepest = 0

	" Accumulate all patterns.
	let all = ''
	if a:openregexp != ''
		let all .= '\|' . a:openregexp
	endif
	if a:closeregexp != ''
		let all .= '\|' . a:closeregexp
	endif
	if a:openextraregexp != ''
		let all .= '\|' . a:openextraregexp
	endif
	if a:closeextraregexp != ''
		let all .= '\|' . a:closeextraregexp
	endif
	if a:hangingregexp != ''
		let all .= '\|' . a:hangingregexp
	endif
	if all == ''
		" No expressions given. Nothing to do.
		return [0,0]
	else
		" Strip the first '\|'
		let all = all[2:]
	end


	" Now, we look through the line for matching patterns
	while pos >= 0
		" Here, we explicitly use the 'count' option of 'matchstrpos' such that
		" '^' matches only at the beginning of the string (and not at 'pos')
		let strpos = matchstrpos( a:line, all, pos, 1 )
		let pos = strpos[2]

		if pos <= 0
			" No more matches were found.
			break
		endif

		" Check if there is an opening or closing match
		let str = strpos[0]

		" Check which pattern has matched
		if str =~ '^' . a:openextraregexp . '$'
			let indent += 2
		elseif str =~ '^' . a:closeextraregexp . '$'
			let indent -= 2
		elseif str =~ '^' . a:openregexp . '$'
			let indent += 1
		elseif str =~ '^' . a:closeregexp . '$'
			let indent -= 1
		else
			" For a hanging line, do not alter indent,
			" but possibly update the deepest indentation
			let deepest = min([deepest, indent - 1])
		endif

		" Update deepest indentation
		let deepest = min([deepest, indent])
	endwhile

	return [deepest, indent - deepest]
endfunction

" Function DeepestNesting:
" This function can be used as indentexpr.
function! Tex_CalcIdent()

	" Current line number
	let clnum = v:lnum

	" Code for comment: If current line is a comment, do not alter the
	" indentation
	let cline = getline(clnum) " Content of current line
	if cline =~ '^\s*%'
		return indent(clnum)
	endif

	" Find a non-blank line above the current line, which is more than a comment.
	let plnum = prevnonblank(clnum - 1)
	while plnum != 0
		if getline(plnum) !~ '^\s*%'
			break
		endif
		let plnum = prevnonblank(plnum - 1)
	endwhile

	" At the start of the file use zero indent.
	if plnum == 0
		return 0
	endif

	let pind = indent(plnum)     " Current indentation of previous line
	let pline = getline(plnum)   " Content of previous line

	" Strip comments
	let pline = substitute(pline, '\\\@<!\(\\\\\)*\zs%.*', '', '')
	let cline = substitute(cline, '\\\@<!\(\\\\\)*\zs%.*', '', '')

	" Add a 'shiftwidth' after beginning
	" and subtract a 'shiftwidth' after the end of environments.
	" Don't add it for \begin{document} and \begin{verbatim}, see
	" g:tex_noindent_env
	let open = '\\begin\s*{\%('.g:tex_noindent_env.'\)\@!.\{-\}}'
	let close = '\\end\s*{\%('.g:tex_noindent_env.'\)\@!.\{-\}}'

	if g:tex_indent_brace
		let open  = open  . '\|[[{(]\|\\left\.'
		let close = close . '\|[]})]\|\\right\.'
	endif

	if g:tex_indent_items
		" For itemize-like environments: add or subtract two 'shiftwidth'
		let extra_open = '\\begin\s*{\%('.g:tex_itemize_env.'\)\*\?}'
		let extra_close = '\\end\s*{\%('.g:tex_itemize_env.'\)\*\?}'

		" Special treatment for items, they will hang
		let hanging = g:tex_items
	else
		" Extra environment indentation
		let extra_open = ''
		let extra_close = ''

		" No hanging expression
		let hanging = ''
	endif

	if g:tex_indent_ifelsefi
		" Do match '\if..' only if it is not followed by '{'
		" Require \fi, and \if... only at beginning of line
		" Exception: '\expandafter\ifx\csname barfoo \endcsname'
		"            is quite common and indented.
		let open .= '\|^\s*\%(\\expandafter\)\?\\if\a*\>{\@!'
		let close .= '\|^\s*\\fi\>'
		let elseor = '\\else\>\|\\or\>'
		if hanging != ''
			let hanging = elseor . '\|' . hanging
		else
			let hanging = elseor
		end
	end

	" Wrap open and close in parentheses
	let open  = '\%(' . open  . '\)'
	let close = '\%(' . close . '\)'

	" Wrap hanging in parentheses, match only at beginning of line
	let hanging = '^\s*\%(' . hanging . '\)'

	" Compute the deepest indentation on the current line
	let indent_this = s:DeepestNesting( cline, open, close, extra_open, extra_close, hanging )
	" Compute the offset to the deepest indentation from the previous line
	let indent_prev = s:DeepestNesting( pline, open, close, extra_open, extra_close, hanging )

	" Add one shiftwidth per indentation level
	let ind = pind + &shiftwidth * ( indent_this[0] + indent_prev[1] )

	return ind
endfunction

" vim: set noet:
