import importlib, inspect
from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from tastypie.resources import Resource
from tastypie import fields
from ._base import CommandMixin

app_tmpl = '''///
/// @file      application.js
/// @namespace {namespace}
///
/// Defintion of the main application.
///

define(
    [ 'jquery', 'knockout', 'models' ],
    function( $, ko, models ) {{

	///
	/// The primary application.
	///
	var Application = Class( _.extend({{

            ///
            /// Construct a new Application.
            ///
	    create: function() {{
		var self = this;

		// Data for the application is passed through the HTML DOM as
		// JSON. Parse it and store it as JavaScript data here.
		this._data = $.parseJSON( window.server_data || '{{}}' );

		// Do some AJAX preparation in order to user CSRF tokens with
		// Django.
		this.csrf_token = $.cookie( 'csrftoken' ) || 'NO-CSRF-TOKEN';
		function csrfSafeMethod( method ) {{
	    	    return (/^(GET|HEAD|OPTIONS\TRACE)$/.test( method ));
		}}
		$.ajaxSetup({{
	    	    beforeSend: function( xhr, settings ) {{
	    		if( !csrfSafeMethod( settings.type ) && !this.crossDomain )
	    		    xhr.setRequestHeader( 'X-CSRFToken', self.csrf_token );
	    	    }}
		}});

		// Identify changes in logged in state.
		this.auth_state = ko.observable( this.data( 'auth_state', 'logged_out' ) );
                this.fetch_image_state = ko.observable();
	    }},

	    ///
	    /// Extract information from the server data.
	    ///
	    data: function( path, def_value ) {{
		var links = is_empty( path ) ? [] : path.split( '.' );
		var data = this._data;
		for( var ii = 0; ii < links.length; ++ii ) {{
		    if( is_empty( data ) || !data.hasOwnProperty( links[ii] ) )
			return def_value;
		    data = data[links[ii]];
		}}
		return data;
	    }},

	    ///
	    /// Register a user.
	    ///
	    register: function( username, email, password1, password2, success ) {{
		if( this.auth_state() == 'busy' )
		    return;
		this.auth_state( 'busy' );
		var self = this;
		var data;
		if( _.isObject( username ) ) {{
		    data = username;
		    success = email;
		}}
		else {{
		    data = {{
			username: username,
			email: email,
			password1: password1,
			password2: password2
		    }};
		}}
		async_post(
		    this.data( 'api.register' ),
		    data,
		    function( response ) {{
			self.auth_state( 'logged_out' );
			if( success )
			    success( response );
		    }}
		);
	    }},

	    ///
	    /// Log a user in.
	    ///
	    login: function( username, password, success ) {{
		if( this.auth_state() == 'busy' )
		    return;
		this.auth_state( 'busy' );
		var self = this;
		var data;
		if( _.isObject( username ) ) {{
		    data = username;
		    success = password;
		}}
		else
		    data = {{ username: username, password: password }};
		async_post(
		    this.data( 'api.login' ),
		    data,
		    function( response ) {{
			if( response.status == 'success' )
			    self.auth_state( 'logged_in' );
			else
			    self.auth_state( 'logged_out' );
			if( success )
			    success( response );
		    }}
		);
	    }},

	    ///
	    /// Log a user out.
	    ///
	    logout: function( success ) {{
		var self = this;
		if( this.auth_state() == 'logging_in' || this.auth_state() == 'logging_out' )
		    return;
		this.auth_state( 'logging_out' );
		async_post(
		    this.data( 'api.logout' ),
		    {{}},
		    function( response ) {{
			self.auth_state( 'logged_out' );
			if( success )
			    success( response );
		    }}
		);
	    }}

	}}, models ));

	return Application;
    }}
);
'''

class Command(CommandMixin, BaseCommand):
    help = 'Generate JavaScript application'

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)
        values = {
            'namespace': self.namespace,
        }
        self.output(app_tmpl.format(**values), 'application.js')
