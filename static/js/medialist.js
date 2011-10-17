
var aiRating = 1;
var ml_base_url = "/rating/";


function deleteMedia()
{
	//use the combined filter/delete form to post to a different url to delete stuff
	myForm = $("#ml_fod");
	myForm.attr('method','POST');
	myForm.attr('action',$("#ml_delete_url").val());
	myForm.submit();
}

function editDate(re_id,the_date)
{
	datePicker = $("#datepicker");
	if (datePicker) { datePicker.hide(); }
	
	dateText = $("#ml_date_" + re_id);
	
	newHtml = "<input dbid=\""+re_id+"\" id=\"datepicker\" size=\"10\" type=\"text\" value=\""+the_date+"\"/>";
	
	dateText.html(newHtml);
	
	datePicker = $("#datepicker");
	datePicker.datepicker( {
		dateFormat: 'yy-mm-dd',
		changeMonth: true, 
		changeYear: true, yearRange: 'c-10:c',
		defaultDate: the_date,
		onClose: datePickerClosed
		});
	
	datepicker.focus();
}

function datePickerClosed(new_date, inst)
{	
	re_id = $("#datepicker").attr("dbid");
	
	dateText = $("#ml_date_" + re_id);
	dateText.html(new_date + "<img src=\"/static/images/ajax-loader.gif\" />");
	
	//server should update now
	if (!re_id || re_id < 0)
		return; //nothing to do
	
	updateUrl = ml_base_url + re_id + "/update/date/" + new_date;
	
	$.ajax({
		url: updateUrl,
		dataType: "json",
		success: mlDateChangeSuccess
	});
}

function mlDateChangeSuccess(data, textStatus, XmlHttpRequest)
{
	re_id = data.id;
	re_date = data.date;
	
	dateText = $("#ml_date_" + re_id);
	
	newHtml = "<a href=\"javascript:editDate(" + re_id +",'"+re_date+"');\">" +
				re_date + "</a>";
	dateText.html(newHtml);
	
	if (data.error)
		mlError(data.error);
}


function mlfilter()
{
	title = $("#mlfn").val();
	title = title.replace(/^\s*/, "").replace(/\s*$/, "");
	
	if (title.length > 0)
		location.href=".?n="+encodeURIComponent(title);
	else
		location.href=".";
}


function setGuiItemRating(itemId, newRating)
{	
	$("#ml_rating_"+itemId).css("width", (newRating * 8) + "px");
}

function setItemStatus(re_id, newStatus)
{
	if (!re_id || re_id < 0)
		return; //nothing to do
	
	updateUrl = ml_base_url + re_id + "/update/status/" + newStatus;
	
	$("#ml_loader_"+re_id).html("<img src=\"/static/images/ajax-loader.gif\" />");
	
	$.ajax({
		url: updateUrl,
		dataType: "json",
		success: mlItemRatingSuccess
	});
}

function setMediaItemStatus(media_id, newStatus)
{
	if (!media_id || media_id < 0)
		return; //nothing to do
	
	ratingEventId = $("#re_"+media_id).val();
	updateUrl = ml_base_url + "m" + media_id + "r" + ratingEventId + "/update/status/" + newStatus;
	
	$("#ml_loader_"+media_id).html("<img src=\"/static/images/ajax-loader.gif\" />");
	
	$.ajax({
		url: updateUrl,
		dataType: "json",
		success: mlMediaItemRatingSuccess
	});
}

function setItemProgress(re_id, type_id, newProgress)
{
	if (!re_id || re_id < 0)
		return; //nothing to do
	
	updateUrl = ml_base_url + re_id + "/update/progress/type/" + type_id +"/" + newProgress;
	
	$("#ml_loader_"+re_id).html("<img src=\"/static/images/ajax-loader.gif\" />");
	
	$.ajax({
		url: updateUrl,
		dataType: "json",
		success: mlItemRatingSuccess
	});
}

function setMediaItemProgress(media_id, type_id, newProgress)
{
	if (!media_id || media_id < 0)
		return; //nothing to do
	
	ratingEventId = $("#re_"+media_id).val();
	updateUrl = ml_base_url + "m" + media_id + "r" + ratingEventId + "/update/progress/type/" + type_id +"/" + newProgress;
	
	$("#ml_loader_"+media_id).html("<img src=\"/static/images/ajax-loader.gif\" />");
	
	$.ajax({
		url: updateUrl,
		dataType: "json",
		success: mlMediaItemRatingSuccess
	});
}


function setItemRating(re_id, newRating)
{	
	if (!re_id || re_id < 0)
	{
		aiRating = newRating;
		$("#media_rating").val(newRating);
		setGuiItemRating(-1, newRating); //don't ajax the new item
	}
	else if ($("#mrok_"+re_id).val() == 1)
	{	
		updateUrl = ml_base_url + re_id + "/update/rating/" + newRating;
		
		//mlInfo("Calling url: "+updateUrl);
		
		$("#ml_loader_"+re_id).html("<img src=\"/static/images/ajax-loader.gif\" />");
		
		$.ajax({
			url: updateUrl,
			dataType: "json",
			success: mlItemRatingSuccess
		});
		
		setGuiItemRating(re_id, newRating);
	}
}

function setMediaItemRating(media_id, newRating)
{	
	if (!media_id || media_id < 0)
	{
		aiRating = newRating;
		$("#media_rating").val(newRating);
		setGuiItemRating(-1, newRating); //don't ajax the new item
	}
	else if ($("#mrok_"+media_id).val() == 1)
	{	
		ratingEventId = $("#re_"+media_id).val();
		updateUrl = ml_base_url + "m" + media_id + "r" + ratingEventId + "/update/rating/" + newRating;
		
		$("#ml_loader_"+media_id).html("<img src=\"/static/images/ajax-loader.gif\" />");
		
		$.ajax({
			url: updateUrl,
			dataType: "json",
			success: mlMediaItemRatingSuccess
		});
		
		setGuiItemRating(media_id, newRating);
	}
}

function mlMediaItemRatingSuccess(data, textStatus, XmlHttpRequest)
{	
	//update ratingevent id for next time
	$("#re_"+data.media_id).val(data.id);
	
	updateItemRating(data.media_id, data);
}


function mlItemRatingSuccess(data, textStatus, XmlHttpRequest)
{
	updateItemRating(data.id, data);
}

function updateItemRating(row_id, data)
{
	//alert("Success! - "+data.durationEditable+" - "+data.duration);
	
	$("#ml_loader_"+row_id).html("&nbsp;");
	
	$("#ml_status_"+row_id).val(data.status);
	
	$("#mrok_"+row_id).val(data.allow_rating);
	
	if (data.base_status)
	{
		$("#row"+row_id).removeClass();
		$("#row"+row_id).addClass(data.base_status);
	}
	
	//update progress range
	for (var type_id in data.range)
	{
		element = "#ml_progress_"+row_id+"_"+type_id;
		//alert("Data range for type: "+data.range[type_id]+
		//		"\n\nProgress: "+data.progress[type_id]);
		if (data.range[type_id] == 0)
		{
			//not editable
			$(element).html("");
			$(element).attr('disabled', 'disabled');
		}
		else
		{
			$(element).html(data.range[type_id]);
			if (data.progressEditable == 1)
			{
				$(element).removeAttr('disabled');
			}
		}
		
		if (data.progress[type_id] == undefined)
		{
			$(element).val(0);
		}
	}
	
	//update progress values
	for (var type_id in data.progress)
	{
		invalidRange = false;
		try { invalidRange = data.range[type_id] == 0; } catch(err) {}
		
		
		//alert("Key: "+key+" Value: "+data.progress[key]);
		element = "#ml_progress_"+row_id+"_"+type_id;
		$(element).val(data.progress[type_id]);
		
		if (data.progressEditable == 0 || invalidRange)
			$(element).attr('disabled', 'disabled');
		else
		{	
			$(element).removeAttr('disabled');
		}
	}
	
	setGuiItemRating(row_id, data.rating);
	if (data.error)
		mlError(data.error);
}


function mlHideStatus()
{
	$("#ml_msg").css("display","None");
}

function mlError(msg)
{
	$("#ml_msg").removeClass("info");
	$("#ml_msg").removeClass("error");
	
	$("#ml_msg").addClass("error");
	
	$("#ml_msg").html(msg);
	$("#ml_msg").css("display", "block");
	
	setTimeout(mlHideStatus,5000); //hide after 5 seconds
}

function mlInfo(msg)
{
	$("#ml_msg").removeClass("info");
	$("#ml_msg").removeClass("error");
	
	$("#ml_msg").addClass("info");
	
	
	$("#ml_msg").html(msg);
	$("#ml_msg").css("display", "block");
	
	setTimeout(mlHideStatus,5000); //hide after 5 seconds
}

