Name:           mkdocs-kit
Version:        1.0.0
Release:        1%{?dist}
Summary:        A wrapped, highly integrated documentation generation environment

License:        MIT
URL:            https://github.com/mlecabellec/mkdocs-kit

Requires:       graphviz plantuml cairo pango gdk-pixbuf2 glib2 shared-mime-info

%description
MkDocs Kit is a wrapped, highly integrated documentation generation environment
compiled into a single standalone binary.

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{_bindir}
install -m 755 %{_sourcedir}/mkdocs-kit %{buildroot}%{_bindir}/mkdocs-kit

%files
%{_bindir}/mkdocs-kit

%changelog
* Mon Jul 06 2026 Mickael Lecabellec <mickael.lecabellec@gmail.com> - 1.0.0-1
- Initial package
